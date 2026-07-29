#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.BackgroundColor = "Black"
$Host.UI.RawUI.ForegroundColor = "White"
Clear-Host

# --- ANSI helpers ---
$ESC = [char]27
$RST = "$ESC[0m"
$B = "$ESC[1m"
$DIM = "$ESC[2m"
$CY = "$ESC[36m"
$GR = "$ESC[32m"
$RD = "$ESC[31m"
$YL = "$ESC[33m"
$MG = "$ESC[35m"
$WH = "$ESC[97m"

# --- Paths ---
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectDir "backend"
$FrontendDir = Join-Path $ProjectDir "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$TempDir = Join-Path $ProjectDir ".tmp"

# --- Utilities ---
function Test-Admin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Write-Status($color, $icon, $msg) {
    Write-Host "$color[$B$icon$RST$color]$RST $msg"
}

function Write-Info($msg) { Write-Status $CY "INFO" $msg }
function Write-Ok($msg) { Write-Status $GR "OK" $msg }
function Write-Err($msg) { Write-Status $RD "LỖI" $msg }
function Write-Warn($msg) { Write-Status $YL "CẢNH BÁO" $msg }

# Vietnamese step progress helpers (Yellow = in-progress, Green = done)
function Write-Step($msg) { Write-Host "  $YL... $msg$RST" }
function Write-StepDone($msg) { Write-Host "  $GR✔  $msg$RST" }

# Show actionable error then wait for keypress before exiting
function Exit-WithError($msg) {
    Write-Host ""
    Write-Host "$RD  [LỖI] $msg$RST"
    Write-Host "$YL  Nhấn phím bất kỳ để thoát...$RST"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Create a desktop shortcut (only once, asks user first)
function Create-DesktopShortcut {
    $shortcutPath = "$env:USERPROFILE\Desktop\Wealth VN.lnk"
    if (Test-Path $shortcutPath) { return }
    Write-Host ""
    Write-Host "$CY  Bạn có muốn tạo lối tắt trên màn hình nền không? (Y/N)$RST" -NoNewline
    $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Write-Host ""
    if ($key.Character -notmatch '^[yY]') {
        Write-Host "$DIM  Đã bỏ qua tạo lối tắt.$RST"
        return
    }
    try {
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = "$PSScriptRoot\start.bat"
        $shortcut.IconLocation = "shell32.dll,13"
        $shortcut.Description = "Wealth VN - Quản lý tài sản"
        $shortcut.WorkingDirectory = $PSScriptRoot
        $shortcut.Save()
        Write-Host "$GR  Đã tạo lối tắt trên màn hình nền.$RST"
    } catch {
        Write-Warn "Không thể tạo lối tắt: $($_.Exception.Message)"
    }
}

function Show-Typing($text, $color = "Cyan", $delay = 20) {
    foreach ($c in $text.ToCharArray()) {
        Write-Host $c -NoNewline -ForegroundColor $color
        Start-Sleep -Milliseconds $delay
    }
    Write-Host ""
}

function Show-Spinner($msg, $seconds) {
    $frames = @("|", "/", "-", "\\")
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $seconds) {
        $frame = $frames[[math]::Floor(((Get-Date) - $start).TotalSeconds * 2) % 4]
        Write-Host "`r$YL  $msg $frame $RST" -NoNewline
        Start-Sleep -Milliseconds 250
    }
    Write-Host ""
}

function Show-InlineSpinner($msg, $durationSec) {
    $frames = @(">", "v", "<", "^", ".", "o", "O", "0", "*", "+")
    $start = Get-Date
    while (((Get-Date) - $start).TotalSeconds -lt $durationSec) {
        $idx = [math]::Floor(((Get-Date) - $start).TotalSeconds * 4) % 10
        $frame = $frames[$idx]
        Write-Host "`r$CY  $msg $frame $RST" -NoNewline
        Start-Sleep -Milliseconds 250
    }
    Write-Host ""
}

function Show-Progress($percent, $msg) {
    $filled = [math]::Floor($percent / 10)
    $bar = "=" * $filled + "-" * (10 - $filled)
    Write-Host "$GR  [$bar] $percent% $RST $DIM$msg$RST"
}

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

function Stop-ProcessTree($processId) {
    Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $processId } | ForEach-Object {
        Stop-ProcessTree $_.ProcessId
    }
    $p = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($p) { $p | Stop-Process -Force }
}

function Get-FrontendPort {
    for ($port = 5173; $port -le 5180; $port++) {
        $inUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $inUse) { return $port }
    }
    return 5173
}

function Get-LanIp {
    # Prefer the interface used for the default route (active WiFi/Ethernet connection)
    $defaultRoute = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" | Sort-Object RouteMetric | Select-Object -First 1
    if ($defaultRoute) {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $defaultRoute.InterfaceIndex | Where-Object {
            $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*"
        } | Select-Object -First 1).IPAddress
        if ($ip) { return $ip }
    }
    # Fallback: any DHCP/manual non-loopback IPv4 address
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        ($_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual")
    } | Select-Object -First 1).IPAddress
    if (-not $ip) {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
            $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*"
        } | Select-Object -First 1).IPAddress
    }
    return $ip
}

function Test-BackendHealth {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $result = $client.BeginConnect("127.0.0.1", 8000, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(2000, $false)
        if ($success) {
            $client.EndConnect($result)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

# --- Intro animation ---
function Show-Intro {
    Show-Typing "WEALTH VN" "Cyan" 35
    Show-Typing "QUẢN LÝ TÀI SẢN VIỆT NAM" "Green" 25
    Show-Typing "HỆ THỐNG TỰ ĐỘNG KHỞI ĐỘNG" "Magenta" 20
    Write-Host ""
    Show-Progress 10 "khởi tạo giao diện"
    Show-Progress 30 "tải mô-đun hệ thống"
    Show-Progress 50 "kết nối cơ sở dữ liệu"
    Show-Progress 70 "kiểm tra thị trường"
    Show-Progress 100 "sẵn sàng"
}

Show-Intro

Write-Host ""
Write-Host "$CY========================================$RST"
Write-Host "$CY||$RST  $B WEALTH VN $RST$DIM//$RST  $WH QUẢN LÝ TÀI SẢN VIỆT NAM$RST  $CY||$RST"
Write-Host "$CY||$RST  $DIM Hệ thống khởi động tự động - v0.1$RST         $CY||$RST"
Write-Host "$CY========================================$RST"
Write-Host ""

if (-not (Test-Path $TempDir)) { New-Item -ItemType Directory -Path $TempDir -Force | Out-Null }

# --- Python ---
Write-Step "Đang kiểm tra Python..."
$PythonCmd = $null
$pyVersion = $null
if (Test-Command python) {
    $PythonCmd = "python"
    $pyVersion = (& python --version 2>&1)
}
elseif (Test-Command py) {
    $PythonCmd = "py"
    $pyVersion = (& py --version 2>&1)
}

if ($pyVersion) {
    Write-StepDone "$pyVersion đã được cài đặt"
}

if (-not $PythonCmd) {
    Write-Step "Đang cài đặt Python..."
    if (-not (Test-Admin)) {
        Exit-WithError "Cần chạy với quyền Administrator để tự động cài đặt Python."
    }

    $pyInstallOk = $false
    if (Test-Command winget) {
        Show-Spinner "Đang cài Python qua winget" 3
        $wingetArgs = "install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements"
        Start-Process winget -ArgumentList $wingetArgs -Wait -NoNewWindow
        $pyInstallOk = $true
    } else {
        $pyInstaller = Join-Path $TempDir "python-installer.exe"
        try {
            if (-not (Test-Path $pyInstaller)) {
                Show-Spinner "Đang tải Python" 2
                Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
            }
            Show-Spinner "Đang cài Python" 2
            Start-Process $pyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait -NoNewWindow
            $pyInstallOk = $true
        } catch {
            $pyInstallOk = $false
        }
    }
    Refresh-Path
    if (Test-Command python) { $PythonCmd = "python" }
    elseif (Test-Command py) { $PythonCmd = "py" }
    if (-not $PythonCmd) {
        Exit-WithError "Không thể cài đặt Python. Vui lòng tải thủ công từ https://www.python.org/downloads/ và chạy lại."
    }
    $pyVersion = (& $PythonCmd --version 2>&1)
    Write-StepDone "$pyVersion đã được cài đặt"
}

# --- Node.js ---
Write-Step "Đang kiểm tra Node.js..."
$NodeCmd = $null
$nodeVersion = $null
if (Test-Command node) {
    $NodeCmd = "node"
    $nodeVersion = (& node --version 2>&1)
}

if ($nodeVersion) {
    Write-StepDone "Node.js $nodeVersion đã được cài đặt"
}

if (-not $NodeCmd) {
    Write-Step "Đang cài đặt Node.js..."
    if (-not (Test-Admin)) {
        Exit-WithError "Cần chạy với quyền Administrator để tự động cài đặt Node.js."
    }

    $nodeInstallOk = $false
    if (Test-Command winget) {
        Show-Spinner "Đang cài Node.js qua winget" 3
        $wingetArgs = "install OpenJS.NodeJS --silent --accept-package-agreements --accept-source-agreements"
        Start-Process winget -ArgumentList $wingetArgs -Wait -NoNewWindow
        $nodeInstallOk = $true
    } else {
        $nodeInstaller = Join-Path $TempDir "node-installer.msi"
        try {
            if (-not (Test-Path $nodeInstaller)) {
                Show-Spinner "Đang tải Node.js" 2
                Invoke-WebRequest -Uri "https://nodejs.org/dist/v22.11.0/node-v22.11.0-x64.msi" -OutFile $nodeInstaller -UseBasicParsing
            }
            Show-Spinner "Đang cài Node.js" 2
            Start-Process msiexec -ArgumentList "/i `"$nodeInstaller`" /qn" -Wait -NoNewWindow
            $nodeInstallOk = $true
        } catch {
            $nodeInstallOk = $false
        }
    }
    Refresh-Path
    if (Test-Command node) { $NodeCmd = "node" }
    if (-not $NodeCmd) {
        Exit-WithError "Không thể cài đặt Node.js. Vui lòng tải thủ công từ https://nodejs.org/ và chạy lại."
    }
    $nodeVersion = (& $NodeCmd --version 2>&1)
    Write-StepDone "Node.js $nodeVersion đã được cài đặt"
}

# --- Virtual environment ---
if (-not (Test-Path $VenvDir)) {
    Write-Step "Đang tạo môi trường ảo Python..."
    Show-Spinner "Đang tạo venv" 2
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Không thể tạo môi trường ảo Python. Kiểm tra cài đặt Python và thử lại."
    }
}

$dataDir = Join-Path $BackendDir "data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
$envFile = Join-Path $BackendDir ".env"
$envExample = Join-Path $BackendDir ".env.example"
if ((-not (Test-Path $envFile)) -and (Test-Path $envExample)) { Copy-Item $envExample $envFile }

$LogDir = Join-Path $ProjectDir ".logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$backendLog = Join-Path $LogDir "backend_install.log"
$frontendLog = Join-Path $LogDir "frontend_install.log"

# --- Dependencies ---
Write-Step "Đang cài đặt phụ thuộc Python..."
Show-Progress 10 "cập nhật backend"
Write-Info "Ghi log backend: $backendLog"
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$requirementsFile = Join-Path $BackendDir "requirements.txt"
cmd /c "`"$venvPython`" -m pip install -r `"$requirementsFile`" 2>&1" | Tee-Object -FilePath $backendLog
if ($LASTEXITCODE -ne 0) {
    Exit-WithError "Không thể cài đặt phụ thuộc Python. Kiểm tra kết nối Internet và thử lại. Xem log: $backendLog"
}
Write-StepDone "Phụ thuộc Python đã sẵn sàng"

Write-Step "Đang cài đặt phụ thuộc frontend..."
Show-Progress 60 "cài đặt frontend"
Write-Info "Ghi log frontend: $frontendLog"
cmd /c "cd /d `"$FrontendDir`" && npm install 2>&1" | Tee-Object -FilePath $frontendLog
if ($LASTEXITCODE -ne 0) {
    Exit-WithError "Không thể cài đặt phụ thuộc frontend. Kiểm tra kết nối Internet và thử lại. Xem log: $frontendLog"
}
Write-StepDone "Phụ thuộc frontend đã sẵn sàng"
Show-Progress 100 "hoàn tất"

# --- Start backend ---
Write-Step "Đang khởi động backend..."
Write-Info "Khởi động backend API trên http://localhost:8000 ..."
$backendProc = Start-Process -FilePath $venvPython -ArgumentList (Join-Path $BackendDir "main.py") -WorkingDirectory $BackendDir -NoNewWindow -PassThru

# --- Start frontend ---
$frontendPort = Get-FrontendPort
$lanIp = Get-LanIp
if ($lanIp) {
    $env:VITE_LAN_URL = "http://${lanIp}:$frontendPort"
}
$lanHint = if ($lanIp) { " (LAN: http://${lanIp}:$frontendPort)" } else { "" }
Write-Step "Đang khởi động frontend..."
Write-Info "Khởi động frontend UI trên http://localhost:$frontendPort$lanHint ..."
$viteBin = Join-Path $FrontendDir "node_modules\.bin\vite.cmd"
$viteArgs = "--port $frontendPort --host"
if (Test-Path $viteBin) {
    $frontendProc = Start-Process -FilePath $viteBin -ArgumentList $viteArgs -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
} else {
    $frontendProc = Start-Process -FilePath "cmd" -ArgumentList "/c cd /d `"$FrontendDir`" && npm run dev -- --port $frontendPort --host" -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
}

# --- Health check ---
Write-Info "Đang đợi hệ thống sẵn sàng..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    if (Test-BackendHealth) {
        $ready = $true
        break
    }
    Show-InlineSpinner "Đang đợi" 1
}

if ($ready) {
    Write-StepDone "Backend đã khởi động"
    Write-StepDone "Frontend đã khởi động"
    Write-Ok "Hệ thống đã sẵn sàng!"
} else {
    Write-Warn "Không thể xác nhận backend, vẫn mở trình duyệt..."
    Write-Host "$RD  [LỖI] Backend không khởi động được. Kiểm tra cổng 8000 có bị chiếm không.$RST"
}
Start-Process "http://localhost:$frontendPort"

Write-Host ""
Write-Host "$GR  [>>] Ứng dụng đang chạy$RST"
Write-Host "$DIM      Backend :$RST $CY http://localhost:8000$RST"
Write-Host "$DIM      Frontend (PC):$RST $CY http://localhost:$frontendPort$RST"
if ($lanIp) {
    Write-Host "$DIM      Frontend (LAN):$RST $CY http://${lanIp}:$frontendPort$RST"
    Write-Host "$DIM      Mobile / QR   :$RST $CY http://${lanIp}:$frontendPort$RST"
}
Write-Host ""

# Offer desktop shortcut on first successful launch
Create-DesktopShortcut

Write-Host ""
Write-Host "$YL  [Nhấn phím bất kỳ để dừng cả hai server]$RST"
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# --- Shutdown ---
Write-Host ""
if ($backendProc) {
    Write-Step "Đang tắt backend..."
    Stop-ProcessTree $backendProc.Id
    Write-StepDone "Backend đã tắt"
}
if ($frontendProc) {
    Write-Step "Đang tắt frontend..."
    Stop-ProcessTree $frontendProc.Id
    Write-StepDone "Frontend đã tắt"
}

$pyInstaller = Join-Path $TempDir "python-installer.exe"
$nodeInstaller = Join-Path $TempDir "node-installer.msi"
if (Test-Path $pyInstaller) { Remove-Item $pyInstaller -Force }
if (Test-Path $nodeInstaller) { Remove-Item $nodeInstaller -Force }
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host ""
Write-Ok "Đã tắt hoàn toàn. Hẹn gặp lại!"
exit 0
