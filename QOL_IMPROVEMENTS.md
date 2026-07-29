# Wealth VN — QoL Improvements & Product Direction (Remaining)

Items marked ✅ have been implemented. This file now lists only **remaining** work.
Originally synthesized from web research (5 parallel agents) + codebase inventory.

**Implemented in this session (P0 + most of P1):**
- ✅ Git already configured + pre-commit hooks added (`.pre-commit-config.yaml`)
- ✅ TanStack Query persistence fixed (`staleTime`/`gcTime`/`maxAge` aligned to 24h)
- ✅ Centralized query keys factory (`frontend/src/lib/query-keys.ts`)
- ✅ ErrorBoundary added in `App.tsx`
- ✅ Alembic migrations set up (replaces ad-hoc `ALTER TABLE`)
- ✅ Automatic SQLite backup via `VACUUM INTO` (`backend/jobs/backup.py`, daily 02:00)
- ✅ Tenacity retry/backoff on vnstock, gold/FX, news scrapers
- ✅ `Intl`-based Vietnamese formatting (`frontend/src/lib/format.ts`)
- ✅ Dashboard hierarchy: hero net worth, recent activity, empty states with CTAs
- ✅ `start.ps1` polished: per-step progress, actionable errors, desktop shortcut, graceful shutdown
- ✅ React Hook Form + Zod for transaction/income forms
- ✅ TanStack Table v8 + react-virtual for transaction history
- ✅ Zustand UI store (`frontend/src/stores/uiStore.ts`)
- ✅ react-i18next (Vietnamese only, no English) + `Intl` formatters
- ✅ PWA via vite-plugin-pwa (manifest, service worker, installable)
- ✅ FastAPI already at 0.136 (CVE fixed); CORS hardened; `/docs` gated behind `DEBUG`
- ✅ `print()` → `logging` across all source/news/jobs/scripts files
- ✅ Goal-based savings (model + API + service)
- ✅ Dividend tracking (model + API + service)
- ✅ Tax DISPLAY module (estimates only, no auto-calc, Vietnamese disclaimer)
- ✅ Corporate actions tracking (model + service)
- ✅ Hybrid news search: FTS5 BM25 + sqlite-vec + Reciprocal Rank Fusion
- ✅ BGE-M3 embeddings via Ollama (CPU-feasible on i5-12th gen: 20-40 docs/sec, ~50ms/query)
- ✅ GitHub Actions CI (`.github/workflows/ci.yml`)
- ✅ Tauri sidecar scaffold (`src-tauri/`)
- ✅ `AGENTS.md` project guide

---

## Remaining P1 (not yet done)

### Recharts 3 upgrade or ECharts for financial charts
Recharts 2.x is deprecated (npm warns on install). Recharts 3 has built-in `responsive` prop + a11y. If you need candlestick/volume/indicators, switch to `echarts-for-react` — native candlestick, handles millions of points.
Sources: https://github.com/recharts/recharts/releases/tag/v3.0.0

### Sentry crash reporting
`sentry-sdk` (backend) + `@sentry/react` (frontend). Desktop apps crash silently today.
Sources: https://github.com/getsentry/sentry-python

### Vietnamese docs (MkDocs Material) + in-app tour
MkDocs Material in Vietnamese, deployed to GitHub Pages. In-app tour via `react-joyride` for first launch.
Sources: https://github.com/squidfunk/mkdocs-material, https://react-joyride.com/docs/getting-started

---

## P2 — Polish & Differentiation (next 6–12 months)

### React 19 upgrade (incremental)
Use `useOptimistic` for instant transaction updates, `useActionState` for forms. Run `npx codemod react/19/migration-recipe`. Server Components N/A (Vite SPA).
Sources: https://react.dev/blog/2024/04/25/react-19-upgrade-guide

### Frontend testing: Vitest + RTL + Playwright
No tests exist. Add Vitest (Jest-compatible, 4–10x faster) + React Testing Library + Playwright E2E for critical paths (add transaction, view portfolio, export).
Sources: https://scrimba.com/articles/how-to-test-react-apps-2026

### Accessibility audit (axe-core)
Limited ARIA today, no focus management. Add `@axe-core/react` in dev, skip-nav link, focus management on route change, semantic buttons (not `<div onClick>`).
Sources: https://github.com/dequelabs/axe-core

### Risk metrics + VN-Index benchmarking (UI surfacing)
`services/risk_metrics.py` already computes volatility/Sharpe/max-drawdown/beta. Surface them in the UI with VN-Index as benchmark, 6% risk-free rate (VN context). Add Sortino, VaR, Information Ratio.
Sources: https://github.com/algotrade-plutus/protosmartbeta

### PhoBERT sentiment for Vietnamese news
`news/processor.py` does sentiment currently via dictionaries/LLM. PhoBERT hits 81–93% accuracy on CafeF financial news at a fraction of LLM cost. Use for the fast path; reserve LLM for complex cases.
Sources: https://github.com/209sontung/Vietnamese-stock-article-classification

### AI tagging taxonomy + few-shot (ViFinClass)
Design taxonomy: sector (ICB), event type, sentiment, ticker relevance. Few-shot from `duongnghia222/vietnam_finance_news_company_tagged` HF dataset. Confidence threshold → human-in-the-loop correction UI.
Sources: https://doi.org/10.1142/s2717554526500037, https://huggingface.co/datasets/duongnghia222/vietnam_finance_news_company_tagged

### Gemini cost control
Use `gemini-2.5-flash` for tagging ($0.30/$2.50 per 1M), set `thinkingBudget=0` for simple classification, enable prompt caching for repeated system prompts. Reserve `2.5-pro` for complex analysis.
Sources: https://developers.googleblog.com/gemini-2-5-thinking-model-updates

### Multi-source gold (SJC/DOJI/PNJ) + SBV FX rates
`services/gold_fx.py` exists; extend to multi-brand via `vang.today` API. Pull SBV interbank FX rates daily. Bid/ask spread display.
Sources: https://www.vang.today/en/api, https://www.sbv.gov.vn/TyGia/faces/ExchangeRate.jspx

### SQLCipher encryption
Financial data is plaintext in SQLite. Add `sqlcipher3-binary`, passphrase prompt on launch, optional encrypt-existing-DB migration.
Sources: https://github.com/coleifer/sqlcipher3

### Mobile companion (Expo + React Native) — strategic
Vietnam retail investors are 80%+ mobile-first. Build a thin Expo companion sharing the FastAPI backend + generated TS client. Focus on quick actions (add transaction, alerts, portfolio glance).
Sources: https://tovest.com/en-US/blog/report/574433

### Multi-device sync (Syncthing or simple cloud)
Sync `backend/data/wealth.db` across devices. Syncthing = privacy-first P2P (no cloud). Or simple last-write-wins cloud sync.
Sources: https://docs.syncthing.net/users/config.html

### Complete Tauri sidecar implementation
Scaffold exists at `src-tauri/`. To finish: PyInstaller-compile `backend/main.py` to single EXE, configure as Tauri `externalBin` sidecar, spawn on app launch, generate real icons, build NSIS installer with auto-update.
Sources: https://github.com/tauri-apps/tauri-docs/blob/v2/src/content/docs/develop/sidecar.mdx

---

## Product Direction Recommendation

**Stay single-user desktop-first, add mobile companion later.**

Rationale:
- Current architecture (FastAPI + Vite SPA launched via PowerShell) fits desktop perfectly.
- Multi-user SaaS adds auth, cloud hosting, Vietnamese data compliance — not justified for a personal wealth tracker yet.
- Vietnam retail investors are mobile-first for *trading*, but wealth tracking/analysis benefits from desktop's larger screen.
- Roadmap: **Phase 1** (done) = polish desktop distribution, backup/export, git+CI, P0/P1 fixes. **Phase 2** (6mo) = Sentry, Vietnamese docs, in-app tour, risk metrics UI. **Phase 3** (12mo) = Expo mobile companion, multi-device sync, complete Tauri installer, optional premium tier with VNPay/MoMo payments.

**Monetization note:** Vietnamese payment rails (VNPay, MoMo ~50M users, ZaloPay ~30M, VietQR/NAPAS) make a freemium local-only tier viable if you ever go paid. Open-source (MIT) the core first to build trust.

---

## Notes
- 5 pre-existing test failures remain (test_api_crud, test_compare, test_smart_import) — confirmed present before this session's changes, not caused by our work.
- AI/network-dependent tests (test_batch_ai, test_gemini_batch, test_news_processing) require real Gemini API key + network; they timeout without it.
- PWA icon PNGs (`pwa-192x192.png`, `pwa-512x512.png`) still need to be generated and placed in `frontend/public/`.
- `backend.zip` in repo root should be gitignored (currently untracked).
