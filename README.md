# SOLARMAN OpenAPI para Home Assistant

Integração personalizada (HACS) que lê os dados em tempo real de um inversor via
[SOLARMAN OpenAPI](https://globalapi.solarmanpv.com). Cada ponto de dado retornado
por `POST /device/v1.0/currentData` vira um sensor (potência, energia, tensão, corrente etc.).

## Requisitos
- Credenciais de desenvolvedor SOLARMAN: **APP ID** e **APP Secret** (solicite à SOLARMAN).
- E-mail e senha da conta SOLARMAN.
- Número de série (SN) do inversor.

## Instalação via HACS
1. HACS → ⋮ → *Repositórios personalizados* → adicione a URL deste repositório, categoria **Integration**.
2. Instale **SOLARMAN OpenAPI** e reinicie o Home Assistant.
3. *Configurações → Dispositivos e serviços → Adicionar integração → SOLARMAN OpenAPI*.

## Observações
- A senha é convertida em SHA-256 e **somente o hash** é armazenado; a senha em texto puro nunca é salva.
- Intervalo de atualização padrão: 5 min (ajustável em *Configurar*).
- Servidor `global` = `globalapi.solarmanpv.com` (Data Center internacional); `china` = `api.solarmanpv.com`.
- Em `tools/` há um testador em PowerShell para validar suas credenciais fora do HA.
