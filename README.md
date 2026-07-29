# Wealth VN — Phần mềm quản lý tài sản đầu tư tại Việt Nam

Ứng dụng máy tính cá nhân giúp bạn theo dõi toàn bộ tài sản đầu tư (cổ phiếu, vàng, ngoại tệ), ghi thu nhập/chi tiêu, xem tin tức thị trường được gắn nhãn tự động, và phân tích danh mục — tất cả chạy cục bộ trên máy của bạn, dữ liệu không gửi đi đâu.

---

## Tính năng chính

- **Danh mục tài sản**: thêm cổ phiếu, vàng, ngoại tệ, tiền mặt; tự động lấy giá từ vnstock và các nguồn vàng/FX.
- **Giao dịch & thu nhập**: ghi nhận mua/bán, cổ tức, thu nhập, chi tiêu; sửa giao dịch mua chưa có giá tự động.
- **Tổng tài sản ròng**: dashboard hiển thị giá trị danh mục, hoạt động gần đây, empty state có nút hành động.
- **Phân tích & so sánh**: biểu đồ Recharts, backtest, so sánh tài sản, cân bằng lại danh mục (rebalance), chỉ số rủi ro (volatility/Sharpe/max-drawdown/beta vs VN-Index).
- **Tin tức thị trường**: crawler theo lịch (CafeF, VnExpress...), gắn nhãn chủ đề + điểm liên quan, tìm kiếm hybrid FTS5 BM25 + sqlite-vec + Reciprocal Rank Fusion.
- **AI gắn nhãn & tóm tắt**: Gemini (primary) hoặc Ollama cục bộ (fallback) để gắn tag, tóm tắt bài viết, RAG.
- **Cảnh báo giá**: đặt ngưỡng, nhận thông báo trong app.
- **Mục tiêu tiết kiệm, cổ tức, hành động công ty, thuế (ước lượng)**.
- **Nhập/xuất CSV**, smart import (đoán định dạng).
- **PWA**: cài đặt như app trên desktop/mobile, offline cache, banner cài đặt + thông báo offline, tự cập nhật qua service worker.
- **Sao lưu tự động**: `VACUUM INTO` hàng ngày lúc 02:00.
- **Desktop app (Tauri)**: đóng gói thành file cài đặt Windows (NSIS/MSI), tự cập nhật có xác thực chữ ký, không cần PowerShell/Python/Node trên máy người dùng.
- **Toàn bộ giao diện tiếng Việt**, định dạng số/tiền theo `vi-VN`.

---

## Yêu cầu hệ thống

- Windows 10/11 (64-bit)
- Kết nối Internet (để lấy giá/tin tức)
- Khoảng 1 GB ổ cứng trống (thêm ~2 GB RAM nếu dùng Ollama)

> Python 3.13 và Node.js 22 sẽ được **tự cài đặt** nếu máy chưa có (cần quyền Administrator lần đầu).

---

## Cài đặt và chạy (cách dễ nhất — dành cho người dùng)

### Bước 1: Mở thư mục `FinProj` trong File Explorer.

### Bước 2: Nhấp đúp vào `start.bat`.

- Nếu Windows hỏi **"Run anyway?"** → chọn **Run anyway**.
- Nếu hỏi quyền Administrator → chọn **Yes** (cần để tự cài Python/Node.js lần đầu).

### Bước 3: Đợi khởi động

Cửa sổ đen sẽ hiện tiến trình: kiểm tra/cài Python → cài Node.js → tạo venv → `pip install` → `npm install` → khởi động backend + frontend. Lần đầu có thể mất vài phút.

Khi thấy:

```
[>>] Ứng dụng đang chạy
Backend : http://localhost:8000
Frontend: http://localhost:5173
```

trình duyệt sẽ tự mở. Nếu không, mở thủ công `http://localhost:5173`.

> `start.ps1` sẽ hỏi có tạo lối tắt trên Desktop không ở lần chạy đầu.

### Bước 4: Tắt ứng dụng

Quay lại cửa sổ đen, **nhấn phím bất kỳ**. Backend và frontend sẽ tắt sạch. Không nên đóng bằng nút X (có thể để lại tiến trình ngầm).

### Cài đặt như app (PWA — không cần chạy lại `start.bat` mỗi lần)

Sau khi app đang mở trong trình duyệt, bạn có thể cài nó như một ứng dụng:

- **Chrome/Edge desktop**: nhấn icon **Install** trên thanh địa chỉ, hoặc dùng nút **Cài đặt** trên banner hiện trong app. App sẽ mở ra cửa sổ riêng như phần mềm bình thường, có icon trên Desktop/Start Menu.
- **iOS Safari**: nhấn nút **Chia sẻ** → **"Thêm vào màn hình chính"**.
- **Android Chrome**: menu ⋮ → **"Add to Home screen"**.

Sau khi cài, app tự cập nhật qua service worker — khi có bản mới, lần mở tiếp theo sẽ tải asset mới ngầm rồi áp dụng. Hoạt động offline với dữ liệu đã cache.

---

## Cài đặt thủ công (dành cho lập trình viên)

### Yêu cầu
- Python 3.13+, Node.js 22+
- Git (nếu clone repo)

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # rồi chỉnh GEMINI_API_KEY nếu dùng Gemini
python main.py              # chạy tại http://localhost:8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev                 # chạy tại http://localhost:5173
```

Mở `http://localhost:5173` trong trình duyệt. Vite proxy `/api` → `http://localhost:8000`.

### Build production
```powershell
cd frontend
npm run build               # xuất ra frontend/dist
npm run preview             # xem thử bản build
```

---

## Cấu hình AI (tùy chọn nhưng nên có)

Sao chép `backend/.env.example` thành `backend/.env` rồi chỉnh:

### Dùng Google Gemini (khuyến nghị, có API key miễn phí)
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=<api_key_từ_aistudio.google.com/app/apikey>
GEMINI_MODEL=gemini-3.1-flash-lite
```
Lấy key miễn phí tại https://aistudio.google.com/app/apikey.

### Dùng Ollama cục bộ (không gửi dữ liệu ra ngoài)
1. Cài Ollama từ https://ollama.com
2. Tải mô hình:
   ```bash
   ollama pull qwen2.5:1.5b
   ```
3. Trong `.env`:
   ```env
   AI_PROVIDER=ollama
   OLLAMA_ENABLED=true
   OLLAMA_MODEL=qwen2.5:1.5b
   ```
4. (Tùy chọn) Bật embedding cho RAG:
   ```env
   OLLAMA_EMBEDDING_ENABLED=true
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```
   rồi `ollama pull nomic-embed-text`.

Nếu không cấu hình AI, app vẫn gắn nhãn tin tức bằng từ khóa cơ bản.

---

## Dữ liệu lưu ở đâu

```
backend/data/wealth.db      # SQLite WAL — toàn bộ dữ liệu của bạn
backend/data/backups/       # sao lưu tự động hàng ngày
```

**Nên sao lưu thư mục `backend/data/` định kỳ.** Khi cập nhật phần mềm, copy thư mục này ra trước, rồi chép lại vào vị trí cũ sau khi thay code.

---

## Cấu trúc dự án

```
FinProj/
├── start.bat / start.ps1     # launcher tự cài đặt + khởi động
├── backend/
│   ├── api/                  # route FastAPI (assets, transactions, news, ...)
│   ├── services/             # business logic + AI + market data + news
│   ├── jobs/                 # APScheduler: backup, price_updater, news_updater
│   ├── models.py             # bảng SQLModel
│   ├── schemas.py            # Pydantic schemas
│   ├── database.py           # engine + migrate cột + sqlite-vec
│   ├── config.py             # settings từ .env
│   ├── main.py               # entrypoint FastAPI
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Assets, Transactions, Analytics, ...
│   │   ├── components/       # Layout, PwaInstallPrompt, OfflineBanner, ...
│   │   ├── hooks/            # usePwaInstall
│   │   ├── api/              # client functions
│   │   ├── lib/              # query-keys, format, storage
│   │   ├── stores/           # Zustand UI store
│   │   ├── contexts/         # Theme, Toast, AiQueue
│   │   └── i18n/             # tiếng Việt
│   ├── scripts/generate-pwa-icons.mjs  # tạo icon PWA từ favicon.svg
│   ├── public/               # PWA icons, offline.html, manifest
│   ├── vite.config.ts        # Vite + PWA (workbox runtime caching) + proxy /api
│   └── package.json
├── src-tauri/                # Tauri v2 desktop wrapper (sidecar + auto-update)
│   ├── src/main.rs           # spawn sidecar, health check, updater commands
│   ├── capabilities/default.json  # quyền shell/updater/process
│   ├── tauri.conf.json       # bundle + updater config
│   └── README.md             # hướng dẫn build/release desktop app
├── backend/
│   ├── pyinstaller.spec      # đóng gói backend thành sidecar EXE
│   ├── runtime_hook.py       # xác định data dir khi chạy đóng gói
│   └── scripts/build_sidecar.ps1  # build + rename + copy sidecar
├── .github/workflows/
│   ├── ci.yml                # CI: pytest + tsc + vite build + cargo check
│   └── release.yml           # build installer + upload GitHub Release (tag v*.*.*)
├── .pre-commit-config.yaml   # ruff + mypy + pre-commit-hooks
└── AGENTS.md                 # hướng dẫn cho AI agent / contributor
```

---

## Lệnh thường dùng (lập trình viên)

```powershell
# Backend
cd backend
python -m pytest tests/ -v              # chạy test
python -m pytest tests/ --cov=.         # test + coverage
python main.py                          # chạy dev server

# Frontend
cd frontend
npx tsc --noEmit                        # type check
npm run build                           # build production
npm run gen-icons                       # tạo lại icon PWA (nếu đổi favicon.svg)

# Pre-commit (cài một lần: pre-commit install)
pre-commit run --all-files
```

> Lưu ý: dự án **không dùng Alembic** hiện tại. Migration cột mới được xử lý bằng `_ensure_columns()` trong `backend/database.py`. Nếu thêm cột mới, mở rộng hàm đó.

---

## Cài đặt như app desktop (Tauri — không cần PowerShell/Python/Node)

App có thể đóng gói thành file cài đặt Windows (`Wealth VN Setup.exe` hoặc `.msi`). Người dùng cuối chỉ cần chạy file cài đặt một lần, sau đó app mở như phần mềm bình thường từ Start Menu — **không cần `start.bat`, không cần cài Python/Node, không thấy cửa sổ đen**. Tự cập nhật khi có phiên bản mới (có xác thực chữ ký).

### Kiến trúc

```
Wealth VN.exe (Tauri shell, ~10 MB)
├── WebView2 → tải frontend/dist (HTML/JS/CSS tĩnh, không cần Vite)
└── Sidecar: wealth-backend.exe (PyInstaller bundle FastAPI, nghe 127.0.0.1:8000)
    └── Dữ liệu: %APPDATA%\vn.wealth.desktop\wealth-vn\data\wealth.db
```

### Build local (lập trình viên)

Yêu cầu: Rust stable (rustup), Python 3.13 + PyInstaller, Node 22, WebView2 runtime.

```powershell
# 1. Build frontend
cd frontend
npm install && npm run build

# 2. Build + đặt tên sidecar (tự động rename + copy vào src-tauri/binaries/)
powershell -ExecutionPolicy Bypass -File ..\backend\scripts\build_sidecar.ps1

# 3. Build installer (NSIS .exe + MSI)
cd ..\src-tauri
cargo tauri build
# → target/release/bundle/nsis/Wealth VN_0.1.0_x64-setup.exe
# → target/release/bundle/msi/Wealth VN_0.1.0_x64_en-US.msi
```

### Tự cập nhật (auto-update)

1. **Sinh keypair chữ ký** (một lần):
   ```powershell
   cargo tauri signer generate -w ~/.tauri/wealth-vn.key
   # → lưu private key vào GitHub Secret TAURI_SIGNING_PRIVATE_KEY
   # → dán public key vào tauri.conf.json plugins.updater.pubkey
   ```
2. **Cấu hình endpoint** trong `tauri.conf.json` (`plugins.updater.endpoints`) — trỏ tới URL `latest.json` (GitHub Releases, Cloudflare Pages, S3...).
3. **Release phiên bản mới**:
   ```powershell
   git tag v0.2.0
   git push origin v0.2.0
   ```
   → GitHub Actions `release.yml` tự build + ký + upload installer + `latest.json` lên GitHub Release (draft).
4. **Trên máy người dùng**: app kiểm tra endpoint khi mở, nếu có bản mới → prompt "Có phiên bản mới, cập nhật?" → tải + xác thực chữ ký + thay binary + relaunch. Dữ liệu trong `%APPDATA%` không bị ảnh hưởng.

Xem hướng dẫn đầy đủ tại `src-tauri/README.md`.

> **Lưu ý**: `tauri.conf.json` hiện chứa placeholder cho `pubkey` và `OWNER/REPO` endpoint — cần thay giá trị thật trước khi publish lần đầu.

---

## Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|-----------|------------|
| Báo thiếu Python/Node.js | Nhấp phải `start.bat` → Run as administrator. |
| Trình duyệt không tự mở | Mở `http://localhost:5173` thủ công. |
| Cửa sổ đen biến mất ngay | Run as administrator, kiểm tra Internet, xem `logs/`. |
| Trang trắng | Đợi 30 giây rồi F5. |
| Lỗi Gemini 401/403 | Kiểm tra `GEMINI_API_KEY` trong `backend/.env`. |
| Ollama timeout | Đảm bảo `ollama serve` đang chạy, tăng `OLLAMA_TIMEOUT`. |
| Cổng 8000/5173 bận | Tắt app khác đang chiếm cổng, hoặc đổi port trong `config.py`/`vite.config.ts`. |
| Tauri build lỗi "sidecar not found" | Chạy `build_sidecar.ps1` trước `cargo tauri build`. |
| Tauri updater không kiểm tra được | Thay `pubkey` + `endpoints` thật trong `tauri.conf.json`, set `TAURI_SIGNING_PRIVATE_KEY`. |
| WebView2 missing | Cài từ https://developer.microsoft.com/microsoft-edge/webview2/ |

---

## Đóng góp

1. Cài pre-commit: `pre-commit install`
2. Tuân thủ convention trong `AGENTS.md`
3. Backend: dùng `logging`, không dùng `print`
4. Frontend: TanStack Query cho server state, Zustand cho UI state, mọi text tiếng Việt, định dạng số bằng `Intl.NumberFormat('vi-VN')`
5. CI chạy trên Windows — đảm bảo `pytest` và `npx tsc --noEmit` pass trước khi push

---

## Giấy phép

Dự án cá nhân. Liên hệ tác giả để biết chi tiết sử dụng.
