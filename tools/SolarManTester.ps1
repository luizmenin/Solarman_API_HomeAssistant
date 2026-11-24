# SolarMan API Tester - Windows PowerShell 5.1 / .NET Framework (built into Windows)
# No external modules or installations required.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$script:AccessToken = ''
$script:LastTokenResponse = $null

function Add-Label($form, $text, $x, $y, $w=145, $h=22) {
    $c = New-Object System.Windows.Forms.Label
    $c.Text = $text; $c.Location = New-Object System.Drawing.Point($x,$y); $c.Size = New-Object System.Drawing.Size($w,$h)
    $form.Controls.Add($c); return $c
}
function Add-TextBox($form, $x, $y, $w, $h=25, $password=$false) {
    $c = New-Object System.Windows.Forms.TextBox
    $c.Location = New-Object System.Drawing.Point($x,$y); $c.Size = New-Object System.Drawing.Size($w,$h)
    if ($password) { $c.UseSystemPasswordChar = $true }
    $form.Controls.Add($c); return $c
}
function Add-Button($form, $text, $x, $y, $w, $handler) {
    $c = New-Object System.Windows.Forms.Button
    $c.Text = $text; $c.Location = New-Object System.Drawing.Point($x,$y); $c.Size = New-Object System.Drawing.Size($w,32)
    $c.Add_Click($handler); $form.Controls.Add($c); return $c
}
function Write-Log([string]$text) {
    $txtLog.AppendText("[$(Get-Date -Format 'HH:mm:ss')] $text`r`n")
}
function Format-Json([string]$json) {
    try { return (ConvertFrom-Json -InputObject $json | ConvertTo-Json -Depth 30) }
    catch { return $json }
}
function Invoke-SolarmanRequest([string]$url, [string]$method, [hashtable]$headers, [string]$body) {
    $req = [System.Net.HttpWebRequest]::Create($url)
    $req.Method = $method
    $req.ContentType = 'application/json; charset=utf-8'
    $req.Accept = 'application/json'
    $req.Timeout = 30000
    $req.ReadWriteTimeout = 30000
    foreach ($key in $headers.Keys) { $req.Headers[$key] = $headers[$key] }
    if ($method -ne 'GET') {
        $bytes = [Text.Encoding]::UTF8.GetBytes($body)
        $req.ContentLength = $bytes.Length
        $stream = $req.GetRequestStream(); $stream.Write($bytes,0,$bytes.Length); $stream.Close()
    }
    try {
        $resp = $req.GetResponse()
        $reader = New-Object IO.StreamReader($resp.GetResponseStream())
        $content = $reader.ReadToEnd(); $reader.Close()
        $status = [int]$resp.StatusCode; $resp.Close()
        return @{ Status=$status; Content=$content }
    } catch [System.Net.WebException] {
        $ex = $_.Exception
        if ($ex.Response) {
            $resp = $ex.Response
            $reader = New-Object IO.StreamReader($resp.GetResponseStream())
            $content = $reader.ReadToEnd(); $reader.Close()
            $status = [int]$resp.StatusCode; $resp.Close()
            return @{ Status=$status; Content=$content }
        }
        throw $ex
    }
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'SolarMan API Tester'
$form.StartPosition = 'CenterScreen'
$form.Size = New-Object System.Drawing.Size(900,790)
$form.MinimumSize = New-Object System.Drawing.Size(900,790)
$form.Font = New-Object System.Drawing.Font('Segoe UI',9)

$tabs = New-Object System.Windows.Forms.TabControl
$tabs.Location = New-Object System.Drawing.Point(12,12); $tabs.Size = New-Object System.Drawing.Size(860,720)
$form.Controls.Add($tabs)

$tabAuth = New-Object System.Windows.Forms.TabPage; $tabAuth.Text = '1. Autenticação'; $tabs.TabPages.Add($tabAuth)
$tabData = New-Object System.Windows.Forms.TabPage; $tabData.Text = '2. Dados em tempo real'; $tabs.TabPages.Add($tabData)

# Authentication page
Add-Label $tabAuth 'Servidor API:' 20 20 120
$cmbServer = New-Object System.Windows.Forms.ComboBox
$cmbServer.Location = New-Object System.Drawing.Point(165,18); $cmbServer.Size = New-Object System.Drawing.Size(390,25); $cmbServer.DropDownStyle = 'DropDownList'
[void]$cmbServer.Items.Add('https://api.solarmanpv.com')
[void]$cmbServer.Items.Add('https://globalapi.solarmanpv.com')
$cmbServer.SelectedIndex = 1; $tabAuth.Controls.Add($cmbServer) # SOLARMAN confirmou International Data Centre
Add-Label $tabAuth 'APP ID:' 20 58 120
$txtAppId = Add-TextBox $tabAuth 165 56 390
$txtAppId.Text = ''
Add-Label $tabAuth 'APP Secret:' 20 94 120
$txtAppSecret = Add-TextBox $tabAuth 165 92 390 25 $true
Add-Label $tabAuth 'Tipo de login:' 20 132 120
$cmbLogin = New-Object System.Windows.Forms.ComboBox
$cmbLogin.Location = New-Object System.Drawing.Point(165,130); $cmbLogin.Size = New-Object System.Drawing.Size(220,25); $cmbLogin.DropDownStyle = 'DropDownList'
[void]$cmbLogin.Items.Add('E-mail'); [void]$cmbLogin.Items.Add('Telefone celular'); [void]$cmbLogin.Items.Add('Nome de usuário')
$cmbLogin.SelectedIndex = 0; $tabAuth.Controls.Add($cmbLogin)
Add-Label $tabAuth 'E-mail / usuário / celular:' 20 170 145
$txtLogin = Add-TextBox $tabAuth 165 168 390
$lblCountry = Add-Label $tabAuth 'Código do país (ex.: 55):' 20 206 145
$txtCountry = Add-TextBox $tabAuth 165 204 100; $txtCountry.Text = '55'
Add-Label $tabAuth 'Senha da conta:' 20 242 120
$txtPassword = Add-TextBox $tabAuth 165 240 390 25 $true
Add-Label $tabAuth 'Org ID (opcional):' 20 278 120
$txtOrg = Add-TextBox $tabAuth 165 276 180
Add-Label $tabAuth 'Idioma:' 20 314 120
$cmbLanguage = New-Object System.Windows.Forms.ComboBox
$cmbLanguage.Location = New-Object System.Drawing.Point(165,312); $cmbLanguage.Size = New-Object System.Drawing.Size(120,25); $cmbLanguage.DropDownStyle = 'DropDownList'
[void]$cmbLanguage.Items.Add('en'); [void]$cmbLanguage.Items.Add('pt'); [void]$cmbLanguage.Items.Add('zh'); $cmbLanguage.SelectedIndex = 0; $tabAuth.Controls.Add($cmbLanguage)

$btnToken = Add-Button $tabAuth 'Obter Token' 165 355 150 {
    try {
        if ([string]::IsNullOrWhiteSpace($txtAppId.Text) -or [string]::IsNullOrWhiteSpace($txtAppSecret.Text) -or [string]::IsNullOrWhiteSpace($txtLogin.Text) -or [string]::IsNullOrWhiteSpace($txtPassword.Text)) {
            [System.Windows.Forms.MessageBox]::Show('Preencha APP ID, APP Secret, login e senha.','Campos obrigatórios','OK','Warning') | Out-Null; return
        }
        $base = $cmbServer.SelectedItem.ToString().TrimEnd('/')
        $app = [Uri]::EscapeDataString($txtAppId.Text.Trim())
        $lang = [Uri]::EscapeDataString($cmbLanguage.SelectedItem.ToString())
        $url = "$base/account/v1.0/token?appId=$app&language=$lang"
        $sha = [Security.Cryptography.SHA256]::Create()
        $hashBytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($txtPassword.Text))
        $hash = ([BitConverter]::ToString($hashBytes)).Replace('-','').ToLowerInvariant()
        $payload = [ordered]@{ appSecret=$txtAppSecret.Text.Trim(); password=$hash }
        switch ($cmbLogin.SelectedIndex) {
            0 { $payload.email = $txtLogin.Text.Trim() }
            1 { if ([string]::IsNullOrWhiteSpace($txtCountry.Text)) { throw 'Informe o código do país.' }; $payload.countryCode=$txtCountry.Text.Trim(); $payload.mobile=$txtLogin.Text.Trim() }
            2 { $payload.username=$txtLogin.Text.Trim() }
        }
        if (-not [string]::IsNullOrWhiteSpace($txtOrg.Text)) { $orgValue=0L; if (-not [long]::TryParse($txtOrg.Text.Trim(),[ref]$orgValue)) { throw 'Org ID deve ser numérico.' }; $payload.orgId=$orgValue }
        $body = $payload | ConvertTo-Json -Depth 5
        Write-Log "POST $url"
        Write-Log 'POST com appId na URL; appSecret, email/usuário/celular e senha SHA-256 no corpo JSON.'
        $result = Invoke-SolarmanRequest $url 'POST' @{} $body
        $txtAuthResponse.Text = Format-Json $result.Content
        Write-Log "HTTP $($result.Status)"
        $obj = $null; try { $obj = ConvertFrom-Json $result.Content } catch {}
        if ($obj -and $obj.success -and $obj.access_token) {
            $script:AccessToken = [string]$obj.access_token
            $script:LastTokenResponse = $obj
            $lblTokenStatus.Text = 'Token recebido com sucesso. Validade informada: ' + [string]$obj.expires_in + ' segundos.'
            $lblTokenStatus.ForeColor = [System.Drawing.Color]::DarkGreen
            Write-Log 'Autenticação concluída. Token armazenado apenas nesta execução do programa.'
            $tabs.SelectedTab = $tabData
        } else {
            $script:AccessToken = ''; $lblTokenStatus.Text = 'Não foi possível obter o token. Confira a resposta abaixo.'
            $lblTokenStatus.ForeColor = [System.Drawing.Color]::DarkRed
            Write-Log 'A API não retornou um access_token válido.'
        }
    } catch { Write-Log "ERRO: $($_.Exception.Message)"; [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Erro na autenticação','OK','Error') | Out-Null }
}
$lblTokenStatus = Add-Label $tabAuth 'Token ainda não obtido.' 330 360 490 35
$lblTokenStatus.ForeColor = [System.Drawing.Color]::DarkRed
Add-Label $tabAuth 'Resposta da API:' 20 405 150
$txtAuthResponse = New-Object System.Windows.Forms.TextBox
$txtAuthResponse.Location = New-Object System.Drawing.Point(20,430); $txtAuthResponse.Size = New-Object System.Drawing.Size(810,180); $txtAuthResponse.Multiline=$true; $txtAuthResponse.ScrollBars='Both'; $txtAuthResponse.WordWrap=$false; $txtAuthResponse.ReadOnly=$true
$txtAuthResponse.Font = New-Object System.Drawing.Font('Consolas',9); $tabAuth.Controls.Add($txtAuthResponse)
$lblHint = Add-Label $tabAuth 'A senha da conta é convertida para SHA-256 em letras minúsculas antes do envio. O APP Secret e a senha não são salvos em arquivo.' 20 625 810 42
$lblHint.ForeColor = [System.Drawing.Color]::DimGray

# Real-time page
Add-Label $tabData 'Serial Number (SN) do inversor:' 20 25 220
$txtSn = Add-TextBox $tabData 245 23 360
$btnCurrent = Add-Button $tabData 'Consultar geração em tempo real' 245 62 260 {
    try {
        if ([string]::IsNullOrWhiteSpace($script:AccessToken)) { throw 'Obtenha o token na aba Autenticação antes de consultar.' }
        if ([string]::IsNullOrWhiteSpace($txtSn.Text)) { throw 'Informe o Serial Number do inversor.' }
        $base = $cmbServer.SelectedItem.ToString().TrimEnd('/')
        $lang = [Uri]::EscapeDataString($cmbLanguage.SelectedItem.ToString())
        $url = "$base/device/v1.0/currentData?language=$lang"
        # A documentação do endpoint usa deviceSn, enquanto o FAQ da SolarMan
        # alerta que DeviceSN é a grafia correta em alguns parâmetros. Testamos
        # deviceSN primeiro e, em caso de 2101006, tentamos deviceSn automaticamente.
        $headers = @{ Authorization = "Bearer $script:AccessToken" }
        $sn = $txtSn.Text.Trim()
        $payload = @{ deviceSN=$sn } | ConvertTo-Json -Compress
        Write-Log "POST $url | tentativa 1: deviceSN=$sn"
        $result = Invoke-SolarmanRequest $url 'POST' $headers $payload
        $obj = $null; try { $obj = ConvertFrom-Json $result.Content } catch {}
        if ($obj -and [string]$obj.code -eq '2101006') {
            Write-Log 'API retornou 2101006 (invalid param). Repetindo com a grafia deviceSn indicada no exemplo específico do endpoint.'
            $payload = @{ deviceSn=$sn } | ConvertTo-Json -Compress
            Write-Log "POST $url | tentativa 2: deviceSn=$sn"
            $result = Invoke-SolarmanRequest $url 'POST' $headers $payload
            $obj = $null; try { $obj = ConvertFrom-Json $result.Content } catch {}
        }
        $txtDataResponse.Text = Format-Json $result.Content
        Write-Log "Consulta de dados HTTP $($result.Status)"
        if ($result.Status -ge 200 -and $result.Status -lt 300) {
            $lblDataStatus.Text = 'Consulta concluída. Verifique os pontos de dados retornados no JSON.'
            $lblDataStatus.ForeColor = [System.Drawing.Color]::DarkGreen
        } else {
            $lblDataStatus.Text = 'A API retornou erro. Consulte o JSON e o log.'
            $lblDataStatus.ForeColor = [System.Drawing.Color]::DarkRed
        }
    } catch { Write-Log "ERRO: $($_.Exception.Message)"; [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Erro na consulta','OK','Error') | Out-Null }
}
$lblDataStatus = Add-Label $tabData 'Aguardando consulta.' 20 108 800 30
Add-Label $tabData 'Resposta da API (JSON):' 20 145 250
$txtDataResponse = New-Object System.Windows.Forms.TextBox
$txtDataResponse.Location = New-Object System.Drawing.Point(20,172); $txtDataResponse.Size = New-Object System.Drawing.Size(810,400); $txtDataResponse.Multiline=$true; $txtDataResponse.ScrollBars='Both'; $txtDataResponse.WordWrap=$false; $txtDataResponse.ReadOnly=$true
$txtDataResponse.Font = New-Object System.Drawing.Font('Consolas',9); $tabData.Controls.Add($txtDataResponse)
Add-Label $tabData 'A consulta usa POST /device/v1.0/currentData e envia deviceSN e, se receber 2101006, tenta automaticamente deviceSn; ambas as grafias são registradas no log.' 20 590 810 42
Add-Label $tabData 'O retorno contém os pontos de dados disponíveis para esse equipamento, conforme o modelo e a configuração do inversor.' 20 625 810 42

# Persistent diagnostic log at bottom of both tabs
$grpLog = New-Object System.Windows.Forms.GroupBox
$grpLog.Text = 'Log de comunicação'; $grpLog.Location = New-Object System.Drawing.Point(20,665); $grpLog.Size = New-Object System.Drawing.Size(810,1)
# Log window is on the authentication tab response for compactness; a shared log is shown in a separate window.
$btnLog = Add-Button $tabAuth 'Abrir log de comunicação' 650 18 180 { $logForm.ShowDialog() | Out-Null }
$logForm = New-Object System.Windows.Forms.Form
$logForm.Text='Log de comunicação'; $logForm.Size=New-Object System.Drawing.Size(800,400); $logForm.StartPosition='CenterParent'
$txtLog = New-Object System.Windows.Forms.TextBox
$txtLog.Multiline=$true; $txtLog.ReadOnly=$true; $txtLog.ScrollBars='Vertical'; $txtLog.Dock='Fill'; $txtLog.Font=New-Object System.Drawing.Font('Consolas',9)
$logForm.Controls.Add($txtLog)

Write-Log 'SolarMan API Tester iniciado.'
Write-Log 'Preencha as credenciais de desenvolvedor fornecidas pela SolarMan.'
[void]$form.ShowDialog()
