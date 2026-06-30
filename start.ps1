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

$ollamaProc = $null

function Test-OllamaHealth($url) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $uri = [System.Uri]$url
        $result = $client.BeginConnect($uri.Host, $uri.Port, $null, $null)
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

# --- Ollama (local AI tagger) ---
$ollamaEnabled = $true
$ollamaModel = "qwen2.5:1.5b"
$ollamaBaseUrl = "http://localhost:11434"
$ollamaEmbeddingEnabled = $false
$ollamaEmbeddingModel = "nomic-embed-text"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "OLLAMA_ENABLED\s*=\s*true") { $ollamaEnabled = $true }
    if ($envContent -match "OLLAMA_MODEL\s*=\s*([^\s#]+)") { $ollamaModel = $Matches[1].Trim() }
    if ($envContent -match "OLLAMA_BASE_URL\s*=\s*([^\s#]+)") { $ollamaBaseUrl = $Matches[1].Trim() }
    if ($envContent -match "OLLAMA_EMBEDDING_ENABLED\s*=\s*true") { $ollamaEmbeddingEnabled = $true }
    if ($envContent -match "OLLAMA_EMBEDDING_MODEL\s*=\s*([^\s#]+)") { $ollamaEmbeddingModel = $Matches[1].Trim() }
}

if ($ollamaEnabled) {
    if (-not (Test-Command ollama)) {
        Write-Info "Đang cài đặt Ollama..."
        $ollamaInstaller = Join-Path $TempDir "OllamaSetup.exe"
        if (-not (Test-Path $ollamaInstaller)) {
            Show-Spinner "Đang tải Ollama" 2
            Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $ollamaInstaller -UseBasicParsing
        }
        Show-Spinner "Đang cài Ollama" 2
        Start-Process $ollamaInstaller -ArgumentList "/S" -Wait -NoNewWindow
        Refresh-Path
        if (-not (Test-Command ollama)) {
            Write-Warn "Không thể cài đặt Ollama tự động. Vui lòng cài thủ công từ https://ollama.com. Hệ thống sẽ dùng tagger từ khóa."
        } else {
            Write-Ok "Ollama đã được cài đặt"
        }
    }

    if (Test-Command ollama) {
        $ollamaRunning = Test-OllamaHealth $ollamaBaseUrl
        if (-not $ollamaRunning) {
            Write-Info "Đang khởi động Ollama server..."
            $ollamaProc = Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -PassThru
            for ($i = 0; $i -lt 30; $i++) {
                if (Test-OllamaHealth $ollamaBaseUrl) {
                    $ollamaRunning = $true
                    break
                }
                Start-Sleep -Seconds 1
            }
            if (-not $ollamaRunning) {
                Write-Warn "Không thể khởi động Ollama server. Hệ thống sẽ dùng tagger từ khóa."
            }
        }

        if ($ollamaRunning) {
            $modelList = & ollama list 2>$null | Out-String
            if ($modelList -notmatch [regex]::Escape($ollamaModel)) {
                Write-Info "Đang tải model $ollamaModel..."
                & ollama pull $ollamaModel
                if ($LASTEXITCODE -ne 0) {
                    Write-Warn "Tải model $ollamaModel thất bại. Hệ thống sẽ dùng tagger từ khóa."
                } else {
                    Write-Ok "Đã tải model $ollamaModel"
                }
            } else {
                Write-Ok "Model $ollamaModel đã có sẵn"
            }

            if ($ollamaEmbeddingEnabled) {
                if ($modelList -notmatch [regex]::Escape($ollamaEmbeddingModel)) {
                    Write-Info "Đang tải model embedding $ollamaEmbeddingModel..."
                    & ollama pull $ollamaEmbeddingModel
                    if ($LASTEXITCODE -ne 0) {
                        Write-Warn "Tải model embedding $ollamaEmbeddingModel thất bại. RAG tương tự bài viết sẽ không hoạt động."
                    } else {
                        Write-Ok "Đã tải model embedding $ollamaEmbeddingModel"
                    }
                } else {
                    Write-Ok "Model embedding $ollamaEmbeddingModel đã có sẵn"
                }
            }
        }
    }
} else {
    Write-Info "Ollama chưa được bật (OLLAMA_ENABLED=false). Hệ thống sẽ dùng tagger từ khóa."
}

# --- Dependencies ---
Write-Info "Cài đặt / cập nhật thư viện backend..."
Show-Progress 10 "cập nhật backend"
$venvPython = Join-Path $VenvDir "Scripts\python.exe"
& $venvPython -m pip install -q -r (Join-Path $BackendDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Err "Cài đặt thư viện backend thất bại."
    exit 1
}

$nodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Info "Cài đặt thư viện frontend..."
    Show-Progress 60 "cài đặt frontend"
    & npm install --prefix $FrontendDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Cài đặt thư viện frontend thất bại."
        exit 1
    }
}
Show-Progress 100 "hoàn tất"

# --- Start backend ---
Write-Info "Khởi động backend API trên http://localhost:8000 ..."
$backendProc = Start-Process -FilePath $venvPython -ArgumentList (Join-Path $BackendDir "main.py") -WorkingDirectory $BackendDir -NoNewWindow -PassThru

# --- Start frontend ---
$frontendPort = Get-FrontendPort
Write-Info "Khởi động frontend UI trên http://localhost:$frontendPort ..."
$viteBin = Join-Path $FrontendDir "node_modules\.bin\vite.cmd"
if (Test-Path $viteBin) {
    $frontendProc = Start-Process -FilePath $viteBin -ArgumentList "--port $frontendPort" -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
} else {
    $frontendProc = Start-Process -FilePath "cmd" -ArgumentList "/c cd /d `"$FrontendDir`" && npm run dev -- --port $frontendPort" -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
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
Write-Host "$DIM      Frontend:$RST $CY http://localhost:$frontendPort$RST"
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
