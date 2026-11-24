# SOLARMAN OpenAPI for Home Assistant

Home Assistant custom integration (HACS) for the SOLARMAN OpenAPI. Add a data logger, import multiple inverters, and set each inverter's generation share (%). Get real-time sensors per inverter plus share-weighted power and energy totals, ready for the Energy dashboard. Cloud polling, password stored as a hash only.

🇬🇧 [English](#english) · 🇧🇷 [Português](#português)

---

## English

### Requirements
- **APP ID and APP Secret** (OpenAPI developer credentials). See [How to get them](#how-to-get-the-app-id-and-app-secret).
- Your SOLARMAN account e-mail and password.
- The **logger SN** (and, if automatic discovery does not work, the inverter SNs).

### How to get the APP ID and APP Secret
They are not generated in the SOLARMAN app or website. **Contact SOLARMAN support** (help center: <https://helpcenter.solarmanpv.com>) and ask for **OpenAPI access** for your account. They will provide the APP ID and APP Secret and confirm which server your account uses (international accounts use `globalapi.solarmanpv.com`, i.e. the `global` option). Keep the APP Secret private and never publish it.

### Installation (HACS)
1. HACS → ⋮ → *Custom repositories* → add this repository URL, category **Integration**.
2. Install **SOLARMAN OpenAPI** and restart Home Assistant.
3. *Settings → Devices & services → Add integration → SOLARMAN OpenAPI*.

### Several inverters and generation share (%)
1. Enter the logger SN. The integration tries to list its inverters; if it cannot, fill in *Inverter SNs*.
2. Select which inverters to import.
3. Enter each inverter's **share (%)** of the generation.

Each inverter becomes a device with all its sensors (**raw** values). The logger becomes a device with three share-weighted sensors that sum `value × % / 100` over the inverters:

| Sensor | Use |
|---|---|
| Power with share (W) | instantaneous power |
| Daily energy with share (kWh) | daily production |
| Total energy with share (kWh) | **use this one in the Energy dashboard** |

Everything can be changed later under *Configure* (inverters, percentages, update interval, data keys).

### Data keys
The data point used by the weighted sensors depends on the inverter model. There is automatic detection (`APo_t1`, `Etdy_ge1`, `Et_ge0`, …). If a sensor shows *unavailable*, look up the key on the inverter's raw sensors (the `unique_id` ends with the key) and enter it under *Configure*.

### Notes
- Weighted sensors become unavailable if **any** selected inverter fails to update, to avoid false drops in the energy counter.
- Changing a share (%) changes the accumulated value; the Energy dashboard may read it as a meter reset. Set the percentage once.
- The password is converted to SHA-256 and **only the hash** is stored.
- Default update interval: 5 min. Server `global` = `globalapi.solarmanpv.com`; `china` = `api.solarmanpv.com`.
- Automatic discovery uses `/station/v1.0/list` and `/station/v1.0/device`, which are not confirmed in the public docs; if it fails, enter the SNs manually.
- `tools/` contains a PowerShell tester to validate your credentials outside Home Assistant.

---

## Português

### Requisitos
- **APP ID e APP Secret** (credenciais de desenvolvedor da OpenAPI). Veja [Como obtê-los](#como-obter-o-app-id-e-o-app-secret).
- E-mail e senha da sua conta SOLARMAN.
- O **SN do logger** (e, se a descoberta automática não funcionar, os SNs dos inversores).

### Como obter o APP ID e o APP Secret
Eles não são gerados no aplicativo nem no site da SOLARMAN. **Entre em contato com o suporte da SOLARMAN** (central de ajuda: <https://helpcenter.solarmanpv.com>) e solicite o **acesso à OpenAPI** para a sua conta. Eles fornecem o APP ID e o APP Secret e informam qual servidor a sua conta usa (contas internacionais usam `globalapi.solarmanpv.com`, ou seja, a opção `global`). Mantenha o APP Secret em sigilo e nunca o publique.

### Instalação (HACS)
1. HACS → ⋮ → *Repositórios personalizados* → URL deste repositório, categoria **Integration**.
2. Instale **SOLARMAN OpenAPI** e reinicie o Home Assistant.
3. *Configurações → Dispositivos e serviços → Adicionar integração → SOLARMAN OpenAPI*.

### Vários inversores e participação (%)
1. Informe o SN do logger. A integração tenta listar os inversores; se não conseguir, preencha *SNs dos inversores*.
2. Selecione quais inversores importar.
3. Informe a **participação (%)** de cada um na geração.

Cada inversor vira um dispositivo com todos os seus sensores (valores **brutos**). O logger vira um dispositivo com três sensores ponderados, que somam `valor × % / 100` de cada inversor:

| Sensor | Uso |
|---|---|
| Potência com participação (W) | potência instantânea |
| Energia do dia com participação (kWh) | produção diária |
| Energia total com participação (kWh) | **use este no painel de Energia** |

Tudo pode ser alterado depois em *Configurar* (inversores, percentuais, intervalo, chaves de dados).

### Chaves de dados
O ponto de dado usado nos sensores ponderados varia conforme o modelo. Há detecção automática (`APo_t1`, `Etdy_ge1`, `Et_ge0`, …). Se algum sensor ficar *indisponível*, veja a chave nos sensores brutos do inversor (o `unique_id` termina com a chave) e informe-a em *Configurar*.

### Observações
- Os sensores ponderados ficam indisponíveis se **qualquer** inversor selecionado falhar na atualização, para não gerar quedas falsas no contador de energia.
- Alterar a participação (%) muda o valor acumulado; o painel de Energia pode interpretar como reinício do medidor. Defina o percentual uma vez.
- A senha é convertida em SHA-256 e **somente o hash** é armazenado.
- Intervalo padrão: 5 min. Servidor `global` = `globalapi.solarmanpv.com`; `china` = `api.solarmanpv.com`.
- A descoberta automática usa `/station/v1.0/list` e `/station/v1.0/device`, não confirmados na documentação pública; se falhar, informe os SNs manualmente.
- Em `tools/` há um testador em PowerShell para validar as credenciais fora do Home Assistant.

---

MIT License
