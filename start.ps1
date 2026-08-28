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

# --- Đồng bộ mã nguồn web-base ---
if (-not (Test-Command git)) {
    Write-Warn "Git chưa được cài đặt. Bỏ qua bước đồng bộ mã nguồn."
} else {
    Write-Info "Đồng bộ mã nguồn mới nhất từ nhánh web-base..."

    # --- Backup user data before sync (git reset --hard would wipe tracked files) ---
    $dbPath = Join-Path $BackendDir "data\wealth.db"
    $dbBackup = Join-Path $TempDir "wealth.db.bak"
    $dbWalPath = Join-Path $BackendDir "data\wealth.db-wal"
    $dbShmPath = Join-Path $BackendDir "data\wealth.db-shm"
    $dbWalBackup = Join-Path $TempDir "wealth.db-wal.bak"
    $dbShmBackup = Join-Path $TempDir "wealth.db-shm.bak"
    $hasBackup = $false
    if (Test-Path $dbPath) {
        Copy-Item $dbPath $dbBackup -Force
        if (Test-Path $dbWalPath) { Copy-Item $dbWalPath $dbWalBackup -Force }
        if (Test-Path $dbShmPath) { Copy-Item $dbShmPath $dbShmBackup -Force }
        $hasBackup = $true
        Write-Info "Đã sao lưu cơ sở dữ liệu người dùng trước khi đồng bộ."
    }

    $currentBranch = $(git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    if ($currentBranch -ne "web-base") {
        Write-Info "Đang chuyển sang nhánh web-base..."
        git checkout web-base 2>&1 | ForEach-Object { Write-Host $_ }
    }

    Show-Spinner "Đang kéo mã nguồn mới nhất" 3
    git fetch origin web-base 2>&1 | ForEach-Object { Write-Host $_ }

    # Use reset --hard for reliable auto-update (end users don't edit source code).
    # Local code changes are discarded; user data is restored from backup below.
    git reset --hard origin/web-base 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Mã nguồn đã cập nhật theo web-base"
    } else {
        Write-Warn "Không thể đồng bộ mã nguồn mới nhất. Bỏ qua."
    }

    # --- Restore user data after sync ---
    if ($hasBackup -and (Test-Path $dbBackup)) {
        $dataDirRestore = Join-Path $BackendDir "data"
        if (-not (Test-Path $dataDirRestore)) { New-Item -ItemType Directory -Path $dataDirRestore -Force | Out-Null }
        Copy-Item $dbBackup $dbPath -Force
        if (Test-Path $dbWalBackup) { Copy-Item $dbWalBackup $dbWalPath -Force }
        if (Test-Path $dbShmBackup) { Copy-Item $dbShmBackup $dbShmPath -Force }
        Write-Ok "Đã khôi phục cơ sở dữ liệu người dùng."
    }
}

# --- Python ---
$PythonCmd = $null
if (Test-Command python) { $PythonCmd = "python" }
elseif (Test-Command py) { $PythonCmd = "py" }

if (-not $PythonCmd) {
    Write-Info "Đang cài đặt Python..."
    if (-not (Test-Admin)) {
        Write-Err "Cần chạy với quyền Administrator để tự động cài đặt Python."
        exit 1
    }

    if (Test-Command winget) {
        Show-Spinner "Đang cài Python qua winget" 3
        $wingetArgs = "install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements"
        Start-Process winget -ArgumentList $wingetArgs -Wait -NoNewWindow
    } else {
        $pyInstaller = Join-Path $TempDir "python-installer.exe"
        if (-not (Test-Path $pyInstaller)) {
            Show-Spinner "Đang tải Python" 2
            Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe" -OutFile $pyInstaller -UseBasicParsing
        }
        Show-Spinner "Đang cài Python" 2
        Start-Process $pyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1" -Wait -NoNewWindow
    }
    Refresh-Path
    if (Test-Command python) { $PythonCmd = "python" }
    elseif (Test-Command py) { $PythonCmd = "py" }
    if (-not $PythonCmd) {
        Write-Err "Không thể cài đặt Python. Vui lòng khởi động lại và chạy lại."
        exit 1
    }
}
Write-Ok "Python đã sẵn sàng"
& $PythonCmd --version

# --- Node.js ---
$NodeCmd = $null
if (Test-Command node) { $NodeCmd = "node" }

if (-not $NodeCmd) {
    Write-Info "Đang cài đặt Node.js..."
    if (-not (Test-Admin)) {
        Write-Err "Cần chạy với quyền Administrator để tự động cài đặt Node.js."
        exit 1
    }

    if (Test-Command winget) {
        Show-Spinner "Đang cài Node.js qua winget" 3
        $wingetArgs = "install OpenJS.NodeJS --silent --accept-package-agreements --accept-source-agreements"
        Start-Process winget -ArgumentList $wingetArgs -Wait -NoNewWindow
    } else {
        $nodeInstaller = Join-Path $TempDir "node-installer.msi"
        if (-not (Test-Path $nodeInstaller)) {
            Show-Spinner "Đang tải Node.js" 2
            Invoke-WebRequest -Uri "https://nodejs.org/dist/v22.11.0/node-v22.11.0-x64.msi" -OutFile $nodeInstaller -UseBasicParsing
        }
        Show-Spinner "Đang cài Node.js" 2
        Start-Process msiexec -ArgumentList "/i `"$nodeInstaller`" /qn" -Wait -NoNewWindow
    }
    Refresh-Path
    if (Test-Command node) { $NodeCmd = "node" }
    if (-not $NodeCmd) {
        Write-Err "Không thể cài đặt Node.js. Vui lòng khởi động lại và chạy lại."
        exit 1
    }
}
Write-Ok "Node.js đã sẵn sàng"
& $NodeCmd --version

# --- Virtual environment ---
if (-not (Test-Path $VenvDir)) {
    Write-Info "Tạo môi trường ảo Python..."
    Show-Spinner "Đang tạo venv" 2
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Tạo môi trường ảo thất bại."
        exit 1
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
Write-Info "Cài đặt / cập nhật thư viện backend..."
Show-Progress 10 "cập nhật backend"
Write-Info "Ghi log backend: $backendLog"
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
$requirementsFile = Join-Path $BackendDir "requirements.txt"
cmd /c "`"$venvPython`" -m pip install -r `"$requirementsFile`" 2>&1" | Tee-Object -FilePath $backendLog
if ($LASTEXITCODE -ne 0) {
    Write-Err "Cài đặt thư viện backend thất bại. Xem log: $backendLog"
    exit 1
}
Write-Ok "Thư viện backend đã cập nhật"

Write-Info "Cài đặt / cập nhật thư viện frontend..."
Show-Progress 60 "cài đặt frontend"
Write-Info "Ghi log frontend: $frontendLog"
cmd /c "cd /d `"$FrontendDir`" && npm install 2>&1" | Tee-Object -FilePath $frontendLog
if ($LASTEXITCODE -ne 0) {
    Write-Err "Cài đặt thư viện frontend thất bại. Xem log: $frontendLog"
    exit 1
}
Write-Ok "Thư viện frontend đã cập nhật"
Show-Progress 100 "hoàn tất"

# --- Start backend ---
Write-Info "Khởi động backend API trên http://localhost:8000 ..."
$backendProc = Start-Process -FilePath $venvPython -ArgumentList (Join-Path $BackendDir "main.py") -WorkingDirectory $BackendDir -NoNewWindow -PassThru

# --- Start frontend ---
$frontendPort = Get-FrontendPort
$lanIp = Get-LanIp
if ($lanIp) {
    $env:VITE_LAN_URL = "http://${lanIp}:$frontendPort"
}
$lanHint = if ($lanIp) { " (LAN: http://${lanIp}:$frontendPort)" } else { "" }
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
    Write-Ok "Hệ thống đã sẵn sàng!"
} else {
    Write-Warn "Không thể xác nhận backend, vẫn mở trình duyệt..."
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
Write-Host "$YL  [Nhấn phím bất kỳ để dừng cả hai server]$RST"
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# --- Shutdown ---
Write-Info "Đang dừng các server..."
if ($backendProc) { Stop-ProcessTree $backendProc.Id }
if ($frontendProc) { Stop-ProcessTree $frontendProc.Id }

$pyInstaller = Join-Path $TempDir "python-installer.exe"
$nodeInstaller = Join-Path $TempDir "node-installer.msi"
if (Test-Path $pyInstaller) { Remove-Item $pyInstaller -Force }
if (Test-Path $nodeInstaller) { Remove-Item $nodeInstaller -Force }
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue }

Write-Ok "Đã dừng. Hẹn gặp lại!"
exit 0
