"""Per-inverter sensors plus logger-level 'participation' sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, KIND_DAILY, KIND_POWER, KIND_TOTAL
from .coordinator import SolarmanCoordinator
from .helpers import to_number

# unit as reported by the API -> (HA unit, device class, state class)
_UNITS: dict[str, tuple[str, SensorDeviceClass | None, SensorStateClass]] = {
    "W": (UnitOfPower.WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "kW": (UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "kWh": (UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "Wh": (UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    "V": (UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    "A": (UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    "Hz": (UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT),
    "℃": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "°C": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "%": (PERCENTAGE, None, SensorStateClass.MEASUREMENT),
}


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create sensors now and whenever new data keys appear."""
    coordinator: SolarmanCoordinator = entry.runtime_data

    async_add_entities(
        SolarmanParticipationSensor(coordinator, kind)
        for kind in (KIND_POWER, KIND_DAILY, KIND_TOTAL)
    )

    known: set[tuple[str, str]] = set()

    def _add_new() -> None:
        new = [
            (sn, key)
            for sn, points in coordinator.data.items()
            for key in (points or {})
            if (sn, key) not in known
        ]
        if new:
            known.update(new)
            async_add_entities(SolarmanSensor(coordinator, sn, key) for sn, key in new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


def _logger_device(coordinator: SolarmanCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"logger_{coordinator.logger_sn}")},
        name=f"SOLARMAN logger {coordinator.logger_sn}",
        manufacturer="SOLARMAN",
        serial_number=coordinator.logger_sn,
    )


class SolarmanSensor(CoordinatorEntity[SolarmanCoordinator], SensorEntity):
    """One raw data point of one inverter (not scaled by participation)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarmanCoordinator, sn: str, key: str) -> None:
        super().__init__(coordinator)
        self._sn = sn
        self._key = key
        item = coordinator.data[sn][key]
        self._attr_unique_id = f"{sn}_{key}"
        self._attr_name = item.get("name") or key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, sn)},
            name=f"SOLARMAN inversor {sn}",
            manufacturer="SOLARMAN",
            serial_number=sn,
            via_device=(DOMAIN, f"logger_{coordinator.logger_sn}"),
        )
        unit = item.get("unit")
        numeric = to_number(item.get("value")) is not None
        if unit in _UNITS and numeric:
            ha_unit, device_class, state_class = _UNITS[unit]
            self._attr_native_unit_of_measurement = ha_unit
            self._attr_device_class = device_class
            self._attr_state_class = state_class
        elif unit and numeric:
            self._attr_native_unit_of_measurement = unit

    def _item(self) -> dict[str, Any] | None:
        return ((self.coordinator.data or {}).get(self._sn) or {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def native_value(self) -> Any:
        item = self._item()
        if item is None:
            return None
        value = item.get("value")
        if self._attr_native_unit_of_measurement or self._attr_device_class:
            return to_number(value)
        return value


_PARTICIPATION = {
    KIND_POWER: (
        "Potência com participação",
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ),
    KIND_DAILY: (
        "Energia do dia com participação",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ),
    KIND_TOTAL: (
        "Energia total com participação",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ),
}


class SolarmanParticipationSensor(CoordinatorEntity[SolarmanCoordinator], SensorEntity):
    """Sum over the selected inverters of value x participation %."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarmanCoordinator, kind: str) -> None:
        super().__init__(coordinator)
        self._kind = kind
        name, unit, device_class, state_class = _PARTICIPATION[kind]
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.logger_sn}_participation_{kind}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = _logger_device(coordinator)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.weighted_total(self._kind)[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        _, contributions = self.coordinator.weighted_total(self._kind)
        return {
            "participation_percent": self.coordinator.shares,
            "contribution": contributions,
        }
