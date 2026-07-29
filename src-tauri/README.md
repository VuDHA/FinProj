# Wealth VN — Tauri Desktop Wrapper

Tauri v2 đóng gói frontend (React) và backend (FastAPI sidecar) thành một ứng
dụng desktop Windows duy nhất, có bộ cài đặt NSIS/MSI và tự động cập nhật.

## Kiến trúc

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Shell (Rust)                    │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │   WebView2   │    │   Sidecar: wealth-backend.exe │   │
│  │  (frontend)  │    │   (FastAPI + Uvicorn)         │   │
│  │              │    │                               │   │
│  │  React +     │◄──►│   http://127.0.0.1:8000       │   │
│  │  Vite build  │HTTP│                               │   │
│  └──────────────┘    └──────────────┬────────────────┘   │
│                                     │                     │
│                                     ▼                     │
│                          ┌────────────────────┐           │
│                          │  SQLite (WAL mode) │           │
│                          │  %APPDATA%\vn.wealth│           │
│                          │  .desktop\wealth-vn│           │
│                          │  \data\wealth.db   │           │
│                          └────────────────────┘           │
└─────────────────────────────────────────────────────────┘
         │
         │  Tauri Updater (kiểm tra latest.json)
         ▼
   GitHub Releases
```

- **Tauri shell** khởi động sidecar `wealth-backend.exe` khi mở app, đợi
  backend health endpoint phản hồi, rồi tải giao diện React vào WebView2.
- **Frontend** gọi API trực tiếp qua `http://127.0.0.1:8000` (axios).
- **Cập nhật**: Tauri kiểm tra endpoint updater khi khởi động, hiển thị
  thông báo nếu có phiên bản mới.

## Yêu cầu để build

| Công cụ | Phiên bản | Mục đích |
|---------|-----------|----------|
| [Rust](https://rustup.rs/) | stable | Biên dịch Tauri shell |
| [Tauri CLI](https://tauri.app/) | v2 | Lệnh `cargo tauri` |
| [Python](https://www.python.org/) | 3.13 | Build sidecar bằng PyInstaller |
| [Node.js](https://nodejs.org/) | 22 | Build frontend (Vite) |
| WebView2 Runtime | — | Có sẵn trên Windows 10/11 |

Cài đặt Tauri CLI:

```powershell
cargo install tauri-cli --version "^2"
```

## Build local (development)

### 1. Build frontend

```powershell
cd frontend
npm ci
npm run build
```

Kết quả: `frontend/dist/` (HTML/CSS/JS tĩnh).

### 2. Build sidecar (backend)

```powershell
cd backend
pip install -r requirements.txt
pip install pyinstaller
pyinstaller pyinstaller.spec --noconfirm
```

Hoặc dùng script hỗ trợ:

```powershell
powershell ..\backend\scripts\build_sidecar.ps1
```

Đổi tên binary cho đúng target-triple suffix mà Tauri yêu cầu:

```powershell
Move-Item -Force backend\dist\wealth-backend.exe `
  src-tauri\binaries\wealth-backend-x86_64-pc-windows-msvc.exe
```

> **Quan trọng**: Tauri yêu cầu sidecar phải có suffix `-{target-triple}.exe`.
> Nếu thiếu suffix, Tauri sẽ không tìm thấy binary khi build.

### 3. Build installer

```powershell
cd src-tauri
cargo tauri build
```

Kết quả:

- **NSIS**: `target/release/bundle/nsis/Wealth VN_0.1.0_x64-setup.exe`
- **MSI**: `target/release/bundle/msi/Wealth VN_0.1.0_x64_en-US.msi`

## Chế độ Dev

```powershell
cd src-tauri
cargo tauri dev
```

Tauri sẽ:

1. Chạy `beforeDevCommand` (`cd ../frontend && npm run dev`) → Vite dev server
   tại `http://localhost:5173`.
2. Biên dịch Rust ở chế độ debug.
3. Mở cửa sổ WebView2 tải từ `devUrl`.

> Sidecar phải được build sẵn và đặt trong `src-tauri/binaries/` trước khi
> chạy `cargo tauri dev`.

## Tự động cập nhật (Auto-update)

### Tạo signing key

```powershell
cargo tauri signer generate -w ~/.tauri/wealth-vn.key
```

Lưu lại:

- **Private key** → đặt vào biến môi trường `TAURI_SIGNING_PRIVATE_KEY`
  (hoặc GitHub Secret cùng tên).
- **Password** (nếu có) → `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`.
- **Public key** → đặt vào `tauri.conf.json` tại
  `plugins.updater.pubkey`.

### Cách hoạt động

1. Khi release, GitHub Actions (`.github/workflows/release.yml`) build
   installer có chữ ký số + tạo file `latest.json` manifest.
2. Tauri-action tải installer + `latest.json` lên GitHub Release (draft).
3. Khi người dùng mở app, Tauri kiểm tra endpoint đã cấu hình trong
   `tauri.conf.json` (`plugins.updater.endpoints`).
4. Nếu có phiên bản mới, app hiển thị thông báo cho người dùng cập nhật.

## Quy trình Release (dành cho maintainer)

1. **Cập nhật version** trong `tauri.conf.json` và `src-tauri/Cargo.toml`.
2. **Commit + tag**:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. **GitHub Actions** tự động chạy `release.yml`:
   - Build frontend + sidecar + Tauri installer.
   - Tải NSIS `.exe`, MSI, và `latest.json` lên **Draft Release**.
4. **Soạn release notes** (tiếng Việt), rồi **Publish** release.
5. Người dùng nhận thông báo cập nhật khi mở app lần tiếp theo.

> Xem SHA256 checksums trong log của workflow để xác minh tính toàn vẹn.

## Vị trí dữ liệu

```
%APPDATA%\vn.wealth.desktop\wealth-vn\data\wealth.db
```

Dữ liệu SQLite được lưu trong `%APPDATA%`, **không bị xóa** khi cập nhật
hoặc gỡ cài đặt.

## Các file cấu hình

| File | Mô tả |
|------|-------|
| `tauri.conf.json` | Cấu hình chính: cửa sổ, bundle targets, sidecar, updater |
| `Cargo.toml` | Dependencies Rust (tauri, tauri-plugin-shell, tauri-plugin-updater) |
| `src/main.rs` | Entry point: spawn sidecar, đăng ký updater commands |
| `capabilities/default.json` | Quyền Tauri v2 (permissions cho shell, updater) |
| `build.rs` | Tauri build script |
| `backend/pyinstaller.spec` | Cấu hình PyInstaller đóng gói sidecar |

## Khắc phục sự cố

### Sidecar không tìm thấy

```
Error: sidecar binary not found
```

**Nguyên nhân**: Binary thiếu target-triple suffix.

**Khắc phục**: Đảm bảo file tên đúng
`wealth-backend-x86_64-pc-windows-msvc.exe` trong `src-tauri/binaries/`.

### WebView2 missing

```
Error: WebView2 runtime not installed
```

**Khắc phục**: Tải và cài đặt WebView2 Runtime từ
<https://developer.microsoft.com/microsoft-edge/webview2/>.

### Lỗi signing

```
Error: TAURI_SIGNING_PRIVATE_KEY not set
```

**Khắc phục**: Kiểm tra biến môi trường `TAURI_SIGNING_PRIVATE_KEY` đã đặt
đúng. Trong CI, kiểm tra GitHub Secret đã được thêm vào repo.

### Antivirus chặn PyInstaller bundle

Một số phần mềm diệt virus có thể flag binary PyInstaller `--onefile` là
nghi ngờ.

**Khắc phục**:

- Thêm exclusion cho thư mục build.
- Hoặc đổi sang `--onedir` trong `pyinstaller.spec` (tạo thư mục thay vì
  file đơn).

## Ghi chú

- **Windows-only**: Hiện tại chỉ hỗ trợ Windows. macOS/Linux sẽ cần đổi
  tên sidecar theo target-triple tương ứng (`x86_64-apple-darwin`,
  `x86_64-unknown-linux-gnu`) và cấu hình bundle targets khác.
- **Frontend ↔ Tauri**: Frontend gọi Tauri commands qua `@tauri-apps/api`
  (`invoke`) cho kiểm tra cập nhật, nhưng dùng HTTP trực tiếp đến
  `localhost:8000` cho các API call thường.
- **WebView2**: Đã có sẵn trên Windows 10/11. Trên Windows cũ hơn cần
  cài đặt thủ công.
