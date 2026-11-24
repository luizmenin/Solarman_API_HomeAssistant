# SOLARMAN OpenAPI for Home Assistant

Home Assistant custom integration (HACS) for the SOLARMAN OpenAPI. Add a data logger, import multiple inverters, and set each inverter's generation share (%). Get real-time sensors per inverter plus share-weighted power and energy totals, ready for the Energy dashboard. Cloud polling, password stored as a hash only.

---

## Português

Integração personalizada (HACS) que lê dados em tempo real de inversores via
[SOLARMAN OpenAPI](https://globalapi.solarmanpv.com). A configuração é feita por **logger**,
que pode ter vários inversores.

## Requisitos
- Credenciais de desenvolvedor SOLARMAN: **APP ID** e **APP Secret**.
- E-mail e senha da conta SOLARMAN.
- SN do logger (e, se a descoberta automática não funcionar, os SNs dos inversores).

## Instalação via HACS
1. HACS → ⋮ → *Repositórios personalizados* → URL deste repositório, categoria **Integration**.
2. Instale **SOLARMAN OpenAPI** e reinicie o Home Assistant.
3. *Configurações → Dispositivos e serviços → Adicionar integração → SOLARMAN OpenAPI*.

## Vários inversores e participação (%)
1. Informe o SN do logger. A integração tenta listar os inversores; se não conseguir, preencha *SNs dos inversores*.
2. Selecione quais inversores importar.
3. Informe a **participação (%)** de cada um na geração.

Cada inversor vira um dispositivo com todos os seus sensores (valores **brutos**). O logger vira um
dispositivo com três sensores já ponderados, somando `valor × % / 100` de cada inversor:

| Sensor | Uso |
|---|---|
| Potência com participação (W) | potência instantânea |
| Energia do dia com participação (kWh) | produção diária |
| Energia total com participação (kWh) | **use este no painel de Energia** |

Tudo pode ser alterado depois em *Configurar* (inversores, percentuais, intervalo).

### Chaves de dados
O ponto de dado usado nos sensores ponderados varia conforme o modelo. Há uma detecção automática
(`APo_t1`, `Etdy_ge1`, `Et_ge0`, …). Se algum ficar *indisponível*, veja a chave nos sensores brutos
do inversor (o `unique_id` termina com a chave) e informe-a em *Configurar*.

## Observações
- Os sensores ponderados ficam indisponíveis se **qualquer** inversor selecionado falhar na atualização, para não gerar quedas falsas no contador de energia.
- Alterar a participação (%) muda o valor acumulado; o painel de Energia pode interpretar como reinício do medidor. Prefira definir o percentual uma vez.
- A senha é convertida em SHA-256 e **somente o hash** é armazenado.
- Intervalo padrão: 5 min. Servidor `global` = `globalapi.solarmanpv.com`; `china` = `api.solarmanpv.com`.
- A descoberta automática usa `/station/v1.0/list` e `/station/v1.0/device`, não confirmados na documentação pública; se falhar, use os SNs manuais.
- Em `tools/` há um testador em PowerShell para validar as credenciais fora do HA.
