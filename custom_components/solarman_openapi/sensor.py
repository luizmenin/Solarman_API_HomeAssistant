"""Sensors created dynamically from the device's real-time data points."""

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

from .const import DOMAIN
from .coordinator import SolarmanCoordinator

# unit as reported by the API -> (HA unit, device class, state class)
_UNITS: dict[str, tuple[str, SensorDeviceClass, SensorStateClass]] = {
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


def _to_number(value: Any) -> float | int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() and "." not in str(value) else number


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create sensors now and whenever new data keys appear."""
    coordinator: SolarmanCoordinator = entry.runtime_data
    known: set[str] = set()

    def _add_new() -> None:
        new = [k for k in coordinator.data if k not in known]
        if new:
            known.update(new)
            async_add_entities(SolarmanSensor(coordinator, k) for k in new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class SolarmanSensor(CoordinatorEntity[SolarmanCoordinator], SensorEntity):
    """One data point of the device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarmanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        item = coordinator.data[key]
        self._attr_unique_id = f"{coordinator.device_sn}_{key}"
        self._attr_name = item.get("name") or key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_sn)},
            name=f"SOLARMAN {coordinator.device_sn}",
            manufacturer="SOLARMAN",
            serial_number=coordinator.device_sn,
        )
        unit = item.get("unit")
        if unit in _UNITS and _to_number(item.get("value")) is not None:
            ha_unit, device_class, state_class = _UNITS[unit]
            self._attr_native_unit_of_measurement = ha_unit
            self._attr_device_class = device_class
            self._attr_state_class = state_class
        elif unit and _to_number(item.get("value")) is not None:
            self._attr_native_unit_of_measurement = unit

    @property
    def available(self) -> bool:
        return super().available and self._key in self.coordinator.data

    @property
    def native_value(self) -> Any:
        item = self.coordinator.data.get(self._key)
        if item is None:
            return None
        value = item.get("value")
        if self._attr_native_unit_of_measurement or self._attr_device_class:
            return _to_number(value)
        return value
