# CommerceQuarry — Product Sourcing & Profitability Platform

## Overview
CommerceQuarry is a high-performance product sourcing and multi-method profitability research platform for e-commerce sellers. It automates product discovery on Amazon, finds supplier candidates across major retail and wholesale marketplaces (Home Depot, Walmart, Lowe's, AliExpress), matches products using deterministic heuristics and DeepSeek AI verification, calculates itemized profitability across four fulfillment methods, provides an interactive review workspace, and exports rich research workbooks.

---

## Implementation Roadmap & Status

| Phase | Milestone | Status | Test Coverage |
|---|---|:---:|:---:|
| **Phase 1** | Project Foundation & Architecture | ✅ Completed | 100% (10/10 tests) |
| **Phase 2** | Core Application Interface & Navigation | ✅ Completed | Verified |
| **Phase 3** | Sourcing Workflow & Orchestration Engine | ✅ Completed | 100% (11/11 tests) |
| **Phase 4** | Demo Mode, Matching Engine & Sourcing Pipeline | ✅ Completed | 100% (35/35 tests) |
| **Phase 5** | Multi-Supplier Candidate Discovery & Confidence Scoring | ✅ Completed | 100% (14/14 tests) |
| **Phase 6** | DeepSeek AI Verification & Resilient Fallback | ✅ Completed | 100% (13/13 tests) |
| **Phase 7** | Profitability Engine & Custom Fee Profiles | ✅ Completed | 100% (15/15 tests) |
| **Phase 8** | Results Management, Detail View & Manual Review Workspace | ✅ Completed | 100% (8/8 tests) |
| **Phase 9** | CSV & 5-Worksheet Excel Exports with Injection Defense | ✅ Completed | 100% (4/4 tests) |
| **Phase 10** | Live Amazon Integration (Modular Provider & Rainforest API) | ✅ Completed | 100% (6/6 tests) |
| **Phase 11** | Live Supplier Integrations (Home Depot, Walmart, Lowe's, AliExpress) | ✅ Completed | 100% (6/6 tests) |

**Total Test Suite:** 122 passing automated tests with 100% pass rate.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 13+, React 18, TypeScript, Tailwind CSS |
| **Backend API** | FastAPI (Python 3.10+) |
| **Database** | Supabase PostgreSQL / SQLAlchemy |
| **Authentication** | Supabase Auth / Bearer token |
| **Background Tasks** | Redis + Celery (with asynchronous thread fallback) |
| **AI Verification** | DeepSeek API (with SHA-256 fingerprint caching & resilience) |
| **Exports** | Python CSV + openpyxl (formula injection defense) |

---

## Key Capabilities

### 1. Sourcing Modes
- **Category Sourcing:** Discovers top-selling products in Amazon categories with custom filters.
- **Seller Sourcing:** Scans seller storefronts (reporting clear capability errors when seller retrieval is unsupported by the provider).
- **Individual Product Sourcing:** Instant lookups via ASIN or Amazon product URLs.

### 2. Multi-Marketplace Supplier Discovery
- Connects **Home Depot**, **Walmart**, **Lowe's**, and **AliExpress**.
- Executes an 8-stage search sequence:
  1. UPC / EAN / GTIN search
  2. Manufacturer Part Number (MPN) search
  3. Model Number search
  4. Brand + Product Name search
  5. Normalized title search
  6. Deduplication across suppliers
  7. Candidate ranking based on identifier match strength & price advantage
  8. Automated candidate pool handoff to matching engine

### 3. Matching & AI Verification Engine
- 4-stage deterministic matching heuristic:
  - Exact UPC / GTIN match (100% confidence)
  - Exact MPN / Model match (95% confidence)
  - Token Jaccard title similarity
  - Pack count discrepancy penalty and model conflict guard
- **DeepSeek AI Verification:**
  - Selective verification policy (skips clear matches and clear mismatches to conserve tokens).
  - Structured prompt generation with missing attributes marked as `N/A`.
  - SHA-256 fingerprint caching and automatic simulation fallback.

### 4. Profitability Engine (4 Fulfillment Methods)
- Independent, simultaneous P&L calculations:
  1. **Amazon FBA:** Tiered cubic feet FBA fees, inbound shipping, prep, packaging, storage.
  2. **Amazon FBM:** Outbound carrier shipping base + weight rate, order handling, prep, packaging.
  3. **Walmart WFS:** WFS base fulfillment fee, inbound rate, prep, packaging, storage.
  4. **Walmart Seller-Fulfilled:** Outbound shipping, handling, packaging.
- Automated selection of the optimal fulfillment method.
- Custom **Fee Profiles** CRUD with cloning and default assignments.
- Break-even price calculator, gross margin %, ROI %, and zero-division guards.

### 5. Results Workspace & Manual Review (Phase 8)
- Real-time search by keyword, title, ASIN, brand, UPC, or MPN.
- Server-side and client-side filtering: min/max profit, min ROI, min margin, supplier, fulfillment method, review status.
- Sorting by Net Profit, ROI %, Margin %, Supplier Cost, Amazon Price, and Match Score.
- **Side-by-Side Product Comparison Modal:**
  - Amazon product vs Supplier candidate listings with images and direct links.
  - Detected discrepancies and differences list.
  - Multi-method P&L comparison cards.
  - Reviewer decision submission (`accepted`, `rejected`, `investigation`) with custom price/pack count corrections.
  - Full reviewer audit trail history.
- Star / bookmarking for tracking top opportunities.

### 6. CSV & Excel Exports (Phase 9)
- **CSV Export:** 22 itemized columns with spreadsheet formula injection defense (escapes `=`, `+`, `-`, `@`, `\t`, `\r`).
- **Excel Workbook (.xlsx):**
  - Sheet 1: `Scan Results` (Full result set)
  - Sheet 2: `Profitable Products` (Filtered profitable opportunities)
  - Sheet 3: `All Matched Products` (Confirmed matches)
  - Sheet 4: `Manual Review` (Ambiguous items requiring verification)
  - Sheet 5: `Rejected Matches` (Rejected candidate listings)
  6. `Scan Summary` (KPI overview, total scanned, matched, profitable, review count, avg profit)
  - Professional openpyxl formatting: frozen headers, auto-filters, currency `$#,##0.00` & percentage `0.0%` formats, and color status badges.

### 7. Modular Integrations (Phase 10 & 11)
- **Amazon Provider:** Abstract interface `AmazonProviderBase` with `DemoAmazonProvider` and `RainforestAmazonProvider` adapters.
- **Supplier Adapters:** `HomeDepotAdapter`, `WalmartAdapter`, `LowesAdapter`, `AliExpressAdapter`.
- Health and capability monitoring endpoints:
  - `GET /api/integrations/amazon/capabilities`
  - `POST /api/integrations/amazon/test`
  - `GET /api/integrations/suppliers/status`
  - `POST /api/integrations/suppliers/{supplier}/test`

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- Python 3.10+
- Git

### Frontend Setup
```bash
cd frontend
npm install
npm run dev   # Starts Next.js on http://localhost:3000
```

### Backend Setup
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload   # API on http://localhost:8000
```

### Running Tests
```powershell
$env:PYTHONPATH=".;backend"
python -m pytest backend/tests/test_*.py -v
```

All 122 tests pass with 100% success rate.
