# CommerceQuarry — Full Implementation Plan

**Document purpose:** Master implementation specification for the CommerceQuarry product-sourcing and profitability research platform.

**Development principle:** Build a complete, testable Demo Mode first. Connect real Amazon and supplier data providers only after the core sourcing, matching, profitability, results, and export workflows work end to end.

---

## 1. Product vision and scope

CommerceQuarry helps sellers:

1. Discover products on Amazon.
2. Find potentially equivalent products from supplier marketplaces.
3. Verify whether supplier listings are genuinely the same product.
4. Calculate profitability across multiple fulfillment methods.
5. Filter, inspect, save, and export sourcing opportunities.

The first release should prioritize a simple, functional workflow over advanced UI polish.

### 1.1 Supported sourcing modes

- **Category sourcing:** Discover products in a selected Amazon category using user-defined filters.
- **Seller sourcing:** Discover products from a seller storefront or seller ID, only when the configured authorized data provider supports seller inventory retrieval.
- **Individual product sourcing:** Search using an ASIN or Amazon product URL.

### 1.2 Initial supplier marketplaces

- Home Depot
- Walmart
- Lowe's
- AliExpress

Supplier availability depends on the provider/API configured for each marketplace. Do not pretend an integration works when it is not configured or does not support the required capability.

### 1.3 Fulfillment methods

- Amazon FBA
- Amazon FBM
- Walmart WFS
- Walmart Seller-Fulfilled

### 1.4 Non-goals for the first MVP

Do not initially build:
- Automated purchasing or ordering.
- Automatic repricing.
- CAPTCHA bypass, bot evasion, or residential proxy rotation.
- Unsupported seller-inventory scraping.
- Complex subscription billing.
- Advanced analytics that depend on unavailable data.

These can be considered separately after the core product is validated.

---

## 2. Technology stack and architecture

Use the following stack unless the existing repository has a strong, documented reason to retain a compatible alternative.

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS |
| Backend API | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| Background jobs | Redis + Celery or equivalent persistent worker queue |
| AI verification | DeepSeek API |
| CSV export | Python standard CSV tooling / pandas where useful |
| Excel export | openpyxl |
| Frontend hosting | Vercel or equivalent |
| Backend and worker hosting | Persistent application hosting |

### 2.1 Architecture rules

- The frontend must not call DeepSeek or marketplace APIs directly.
- All secrets must remain server-side.
- Long-running scans must run in background jobs, not in a single long-lived HTTP request.
- The frontend should receive scan progress through polling, server-sent events, or WebSockets.
- Supplier and Amazon providers must be modular adapters.
- Normalize provider data into internal schemas before passing it to matching and profitability services.
- Demo and live data must be explicitly distinguished.
- The matching engine and profit calculator must be independent of the data provider.
- Persist scan results incrementally so partial results remain available if a worker fails.

### 2.2 Suggested repository layout

```text
commercequarry/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── sourcing/
│   │   │   ├── amazon/
│   │   │   ├── suppliers/
│   │   │   ├── matching/
│   │   │   ├── profitability/
│   │   │   └── exports/
│   │   ├── workers/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── database/
│   └── migrations/
├── docs/
├── IMPLEMENTATION_STATUS.md
└── README.md
```

Adapt this layout to the existing repository rather than duplicating or overwriting working code.

---

## 3. Database design

Create migrations and appropriate indexes, foreign keys, timestamps, and user-level access policies.

### 3.1 Core tables

| Table | Purpose |
|---|---|
| `users` | User profile and account metadata; use Supabase Auth identity |
| `scans` | Scan request, configuration, status, timestamps, and summary |
| `scan_logs` | Progress events, warnings, and errors |
| `amazon_products` | Normalized Amazon product records |
| `supplier_products` | Normalized supplier listing records |
| `product_matches` | Candidate pair, match score, AI decision, and review state |
| `scan_results` | Final product opportunity and calculated results |
| `fee_profiles` | User-defined fulfillment profiles |
| `fee_profile_items` | Individual cost and fee rules |
| `marketplace_fee_schedules` | Versioned marketplace fee data and effective dates |
| `supplier_integrations` | Provider configuration and connection status; never store plaintext secrets |
| `user_settings` | User preferences and defaults |

### 3.2 Important data fields

A scan should store:
- User ID.
- Sourcing mode.
- Category, seller identifier, or ASIN input as applicable.
- Amazon price range.
- Supplier price range.
- Minimum profit, ROI, and margin.
- Maximum products.
- Selected suppliers.
- Selected fulfillment methods.
- Demo/live mode.
- Status and progress counters.
- Start, completion, and cancellation timestamps.
- Error summary.

A scan result should retain:
- Amazon product ID and snapshot.
- Supplier product ID and snapshot.
- Match confidence and decision.
- Match explanation and differences.
- Source/provider identifiers.
- Source retrieval timestamps.
- Price and availability timestamps.
- Fee profile and fee schedule versions used.
- Profit, ROI, margin, and calculation status.
- Whether the data is simulated, estimated, or live.

### 3.3 Security and data isolation

- Enable Supabase Row Level Security on user-owned records.
- Users must only access their own scans, products where appropriate, fee profiles, exports, and settings.
- Validate ownership in backend endpoints as well as database policies.
- Never expose service-role keys in frontend code.
- Do not store API secrets in plaintext database columns. Use server-side environment secrets or a secure secret-management design.

---

# 4. Phase-by-phase implementation

## Phase 1 — Project foundation

**Objective:** Establish a working frontend/backend/database foundation.

### Tasks

1. Inspect the existing repository and identify what is already implemented.
2. Preserve useful existing code; do not blindly replace the project.
3. Set up or verify the frontend and backend projects.
4. Configure environment variables and `.env.example`.
5. Connect FastAPI to Supabase PostgreSQL.
6. Create initial database migrations.
7. Configure authentication and user identity handling.
8. Configure Redis and a background worker.
9. Add health-check endpoints for API, database, and worker status.
10. Add structured logging and consistent API error responses.
11. Add basic automated test setup.
12. Document local setup and commands in README.

### Acceptance criteria

- Frontend starts locally.
- Backend starts locally.
- Frontend can call a backend health endpoint.
- Backend can connect to the database.
- Database migrations run successfully.
- A test background job can be queued and completed.
- Environment secrets are not exposed to the browser.
- README explains how to run the project.

Do not proceed until the foundation is demonstrably working.

---

## Phase 2 — Core application interface

**Objective:** Build the basic application shell and all primary pages.

### Main navigation

1. Dashboard
2. New Product Scan
3. Scan Results
4. Scan History
5. Fee Profiles
6. Integrations
7. Settings

### Dashboard

Show real database-backed metrics:
- Total products scanned.
- Total matched products.
- Profitable opportunities.
- Average ROI.
- Average net profit.
- Recent scans.
- Recent profitable opportunities.
- Scan activity.
- Quick action to start a scan.

For an empty account, show useful empty states rather than fabricated metrics.

### Page requirements

- **New Scan:** sourcing form and scan configuration.
- **Scan Results:** result table, filters, sorting, and details.
- **Scan History:** previous scans, statuses, and summaries.
- **Fee Profiles:** create and edit fulfillment fee profiles.
- **Integrations:** configure and test supported data providers.
- **Settings:** user preferences and default scan settings.

### Acceptance criteria

- Every navigation item opens the correct page.
- Forms validate input.
- Buttons perform their advertised actions.
- Loading, empty, success, and error states are present.
- No primary control is merely decorative.

---

## Phase 3 — Sourcing workflow and scan orchestration

**Objective:** Convert user input into a persisted background scan.

### 3.1 Category sourcing

Allow the user to select an Amazon category and configure:
- Amazon minimum and maximum selling price.
- Supplier minimum and maximum price, if applicable.
- Minimum net profit.
- Minimum ROI.
- Minimum margin.
- Maximum products to scan.
- Supplier marketplaces.
- Fulfillment methods to evaluate.

Provide an extensible category list. Do not imply a category is available from a live provider unless that provider supports it.

### 3.2 Seller sourcing

Allow:
- Seller storefront URL.
- Seller ID.

Validate input and determine whether the configured Amazon provider supports seller inventory retrieval. If unsupported, show a clear capability message and do not create a misleading scan.

### 3.3 Individual product sourcing

Allow:
- ASIN.
- Amazon product URL.

Normalize and validate the input before creating a scan.

### 3.4 Scan lifecycle

Support these statuses:
- `queued`
- `running`
- `completed`
- `completed_with_errors`
- `failed`
- `cancelled`

Create the scan record first, then enqueue a background job. Return the scan ID immediately.

### Acceptance criteria

- All three sourcing modes validate and create scans.
- Jobs are processed by the worker.
- Scan status and progress are persisted.
- Invalid requests return useful errors.
- A user cannot access another user's scan.

---

## Phase 4 — Demo mode and simulation engine

**Objective:** Make the entire product testable without paid data providers.

This phase must use the real application pipeline with simulated provider adapters. Do not merely display a static mock results table.

### 4.1 Demo dataset

Create realistic sample Amazon and supplier records across categories such as:
- Home & Kitchen.
- Tools & Home Improvement.
- Sports & Outdoors.
- Beauty & Personal Care.
- Pet Supplies.
- Electronics accessories.

Include supplier candidates from:
- Home Depot.
- Walmart.
- Lowe's.
- AliExpress.

Sample records should include, where applicable:
- Product title.
- Brand.
- ASIN.
- UPC/EAN/GTIN.
- Manufacturer part number.
- Model number.
- Product URL.
- Image or clearly identified sample image.
- Price.
- Availability.
- Dimensions.
- Weight.
- Color, material, size, and package quantity.

### 4.2 Matching scenarios

Include:
- Exact identifier matches.
- Strong title/specification matches.
- Similar products with different variants.
- Incorrect pack counts.
- Different model numbers.
- Similar titles for unrelated products.
- Missing identifiers and incomplete data.

### 4.3 Demo scan behavior

A Demo Mode scan must:
1. Create a real scan record.
2. Queue and execute a background job.
3. Load simulated Amazon products.
4. Run simulated supplier searches.
5. Normalize the data.
6. Run the actual matching service.
7. Run the actual profitability service.
8. Persist results incrementally.
9. Update progress counters.
10. Display partial and final results.
11. Support cancellation.
12. Support CSV and XLSX export.

All demo records and results must be clearly labeled as simulated.

### Acceptance criteria

A user can start a demo scan and complete the entire workflow without any external marketplace credentials. The same matching, calculation, results, and export services intended for live mode must be exercised.

---

## Phase 5 — Supplier discovery and product matching

**Objective:** Find candidate supplier listings and determine whether they are the same product as the Amazon listing.

### 5.1 Multi-stage matching pipeline

**Stage 1 — Exact identifiers**
- UPC.
- EAN.
- GTIN.
- Manufacturer part number.
- Model number.
- Brand.
- Relevant SKU identifiers.

**Stage 2 — Deterministic text/specification comparison**
- Normalized title.
- Brand.
- Product type.
- Dimensions.
- Color.
- Material.
- Size.
- Quantity and pack count.
- Model and technical specifications.

**Stage 3 — Candidate ranking**

Use deterministic scoring to rank candidates and remove obviously irrelevant listings before AI verification.

**Stage 4 — Final decision**

Accept, reject, or send candidates for manual review. Store the reason for the decision.

### 5.2 Initial confidence bands

| Confidence | Initial treatment |
|---:|---|
| 95–100 | Strong match; eligible for automatic acceptance |
| 80–94 | Likely match; acceptance policy should be configurable |
| 60–79 | Manual review |
| Below 60 | Reject |

These are initial thresholds, not a guarantee of accuracy. Evaluate against manually labeled test data and adjust to reduce false positives.

### 5.3 Critical mismatch checks

Explicitly detect:
- Different model or generation.
- Different size or dimensions.
- Different color or material when meaningful.
- Different package count.
- Single item versus bundle.
- Different included accessories.
- Different voltage, compatibility, or technical specifications.
- Used/refurbished versus new condition.
- Different brand or manufacturer.

### 5.4 Match record

Store:
- Amazon product reference.
- Supplier product reference.
- Deterministic score.
- AI score, if used.
- Final confidence.
- Match type.
- Explanation.
- Differences.
- Manual-review flag.
- Final decision.
- Reviewer decision and notes.
- Timestamp and matching-engine version.

### Acceptance criteria

Tests demonstrate that exact matches are accepted, obvious mismatches are rejected, uncertain cases are routed to review, and each decision has an explanation.

---

## Phase 6 — DeepSeek AI verification

**Objective:** Use DeepSeek selectively to resolve ambiguous candidate matches.

### 6.1 AI usage policy

- Do not send every candidate to AI.
- Run exact identifier and deterministic checks first.
- Send only ambiguous, sufficiently relevant candidates.
- Cache responses by normalized product-pair fingerprint and prompt/model version.
- Set timeouts, retries, and request limits.
- Record token usage and estimated cost where provider data allows.
- Validate the response schema before accepting it.
- Treat model output as a recommendation, not unquestionable truth.

### 6.2 AI input

Provide available structured fields:
- Amazon title, brand, identifiers, dimensions, and specifications.
- Supplier title, brand, identifiers, dimensions, and specifications.
- Quantity, variants, included accessories, and condition.
- Explicitly mark missing or unknown fields.

### 6.3 Required structured output

```json
{
  "is_match": true,
  "confidence": 96,
  "match_type": "exact",
  "reason": "The brand, model, and product specifications align.",
  "differences": [],
  "manual_review": false
}
```

Reject malformed or incomplete responses. Do not let AI invent missing product attributes, supplier prices, Amazon prices, fees, or availability.

### Acceptance criteria

- AI is called only for eligible ambiguous candidates.
- Valid JSON is parsed and validated.
- Invalid responses are safely handled.
- Cached results prevent unnecessary repeat calls.
- AI failures do not crash an entire scan.
- AI decisions and cost metadata are logged where available.

---

## Phase 7 — Profitability calculator and fee profiles

**Objective:** Calculate potential net profit, margin, and ROI for all four fulfillment methods.

### 7.1 Cost inputs

Support:
- Supplier product cost.
- Marketplace referral fees.
- Fulfillment fees.
- Inbound and outbound shipping.
- Prep costs.
- Packaging.
- Storage.
- Labor.
- Warehouse handling.
- Other operational costs.
- Optional taxes or additional user-defined expenses.

### 7.2 Fulfillment methods

Calculate independently for:
1. Amazon FBA.
2. Amazon FBM.
3. Walmart WFS.
4. Walmart Seller-Fulfilled.

Each method must use its own relevant fee profile and marketplace fee assumptions.

### 7.3 Core formulas

```text
Total Expenses =
  Product Cost
  + Marketplace Fees
  + Fulfillment Fees
  + Shipping
  + Prep
  + Packaging
  + Storage
  + Other Operational Expenses

Net Profit = Selling Price - Total Expenses

Margin (%) = (Net Profit / Selling Price) * 100

ROI (%) = (Net Profit / Product Cost) * 100
```

Do not calculate ROI if product cost is missing or zero. Guard against division by zero.

### 7.4 Fee profiles

Allow multiple named profiles, for example:
- Amazon FBA Standard.
- Amazon FBM My Warehouse.
- Walmart WFS Standard.
- Walmart Seller-Fulfilled My 3PL.

Each profile should support:
- Fixed amount.
- Percentage of selling price.
- Per-unit expense.
- Per-order expense.
- Per-day or per-month expense.
- Enable/disable.
- Create, edit, duplicate, and delete.
- Assignment as a default profile.

### 7.5 Fee schedules and uncertainty

- Store fee schedule source and effective date.
- Make fee assumptions editable.
- Do not assume missing fees are zero.
- If dimensions, weight, category, or current fee schedule are missing, mark the calculation estimated or incomplete.
- Clearly separate verified, estimated, and incomplete calculations.
- Prevent double-counting marketplace fees and custom operating costs.
- Keep a breakdown explaining every expense.

### Acceptance criteria

Unit tests verify formulas, fee profile rules, missing-data handling, all four fulfillment methods, and correct best-method selection.

---

## Phase 8 — Results management and manual review

**Objective:** Provide a useful workspace for examining sourcing opportunities.

### 8.1 Results table columns

- Amazon product image.
- Amazon product title.
- ASIN.
- Amazon selling price.
- Supplier marketplace.
- Supplier product title.
- Supplier price.
- Match confidence.
- Match type.
- Match explanation or review indicator.
- Net profit.
- ROI.
- Margin.
- Best fulfillment method.
- Availability/data status.

### 8.2 Filters

Support:
- Minimum/maximum profit.
- Minimum ROI.
- Minimum margin.
- Amazon price range.
- Supplier price range.
- Supplier marketplace.
- Match confidence.
- Match type.
- Fulfillment method.
- Availability.
- Calculation status.
- Demo/live data source.

### 8.3 Sorting and pagination

Support sorting by:
- Highest net profit.
- Highest ROI.
- Highest margin.
- Lowest supplier cost.
- Highest Amazon price.
- Highest match confidence.

Use server-side pagination for large result sets.

### 8.4 Product detail view

Show:
- Amazon product information.
- Supplier product information.
- Product comparison.
- Match explanation.
- Differences and missing fields.
- Fee breakdown for each fulfillment method.
- Profit, ROI, and margin.
- Supplier product link.
- Data source and retrieval timestamp.
- Calculation status.

### 8.5 Manual review

Allow users to:
- Accept a suggested match.
- Reject a suggested match.
- Mark for further investigation.
- Add notes.
- Correct relevant product information where permitted.

Persist reviewer decisions and keep an audit trail. Do not silently overwrite the original provider response.

### Acceptance criteria

Users can search, filter, sort, inspect, and review results. Filters must affect displayed results and exports consistently.

---

## Phase 9 — CSV and Excel exports

**Objective:** Allow users to download complete sourcing research.

### 9.1 CSV fields

Include:
- Amazon product title.
- ASIN.
- Amazon URL.
- Amazon price.
- Supplier name.
- Supplier product title.
- Supplier URL.
- Supplier price.
- Match confidence.
- Match type.
- Match explanation.
- Product differences.
- Marketplace fees.
- Fulfillment fees.
- Other costs.
- Net profit.
- ROI.
- Margin.
- Best fulfillment method.
- Availability.
- Data source.
- Calculation status.
- Scan timestamp.

Protect CSV exports against spreadsheet formula injection by safely escaping untrusted text fields.

### 9.2 Excel workbook

Create worksheets:
1. **Profitable Products** — products passing the selected profitability criteria.
2. **All Matched Products** — all accepted matches.
3. **Manual Review** — uncertain matches.
4. **Rejected Matches** — rejected candidates, where the user chooses to include them.
5. **Scan Summary** — scan configuration and summary statistics.

Use readable column widths, frozen header rows, filters, currency and percentage formatting, and clear status labels.

### 9.3 Export options

- Export all scan results.
- Export currently filtered results.
- Export selected rows.
- Export profitable products only.
- Include or exclude rejected matches.

### Acceptance criteria

CSV and XLSX files open successfully and contain the correct rows, values, formats, and filters. Export endpoints must enforce user ownership.

---

## Phase 10 — Live Amazon integration

**Objective:** Replace simulated Amazon product discovery with real data from a configured authorized provider.

### 10.1 Provider strategy

Implement a provider adapter interface. Evaluate:
- Official Amazon APIs for the exact capabilities they support.
- Authorized third-party product-data providers.
- Licensed product feeds.

Do not assume a product lookup API also supports category discovery or arbitrary seller inventory.

### 10.2 Required capability checks

Before selecting a provider, confirm:
- Individual ASIN/product lookup.
- Category/product discovery.
- Seller inventory retrieval, if required.
- Price availability and update frequency.
- Product identifiers and specifications.
- Images and product URLs.
- Rate limits and pricing.
- Commercial-use and storage rights.
- Geographic/marketplace coverage.

### 10.3 Normalization

Convert provider responses into the internal Amazon product schema. Preserve source identifiers, retrieval timestamps, and field provenance.

### 10.4 Failure behavior

- Clearly identify unavailable fields.
- Retry transient errors with backoff.
- Respect provider rate limits.
- Do not invent or silently substitute prices.
- Mark stale data.
- Preserve partial results if a provider fails partway through a scan.

### Acceptance criteria

A configured authorized provider can complete supported live Amazon lookup workflows through the same pipeline used by Demo Mode. Unsupported capabilities are clearly reported.

---

## Phase 11 — Live supplier integrations

**Objective:** Connect real supplier listings through authorized APIs, feeds, or permitted data providers.

Build a separate adapter for each marketplace:
1. Home Depot.
2. Walmart.
3. Lowe's.
4. AliExpress.

### 11.1 Adapter interface

Where supported, each adapter should implement:
- Product search.
- Product detail lookup.
- Price retrieval.
- Availability retrieval.
- Product image and URL.
- Identifier extraction.
- Variant information.
- Shipping information and cost, if available.
- Provider rate-limit handling.
- Health/connection test.

Not every provider supports every field or operation. Capability differences must be represented explicitly.

### 11.2 Search sequence

For each Amazon product:
1. Search by UPC/EAN/GTIN.
2. Search by manufacturer part number.
3. Search by model number.
4. Search by brand plus product name.
5. Search by normalized title.
6. Normalize and deduplicate candidates.
7. Rank candidates.
8. Pass eligible candidates to matching.

### 11.3 Integration status

Display:
- Connected.
- Not configured.
- Connection error.
- Rate limited.
- Capability unsupported.
- Temporarily unavailable.

Never display fabricated live marketplace results.

### 11.4 Supplier data quality

Record:
- Supplier/provider identity.
- Listing URL.
- Price and currency.
- Availability.
- Variant.
- Shipping cost and delivery estimate when provided.
- Retrieval timestamp.
- Data freshness.
- Any missing critical fields.

### Acceptance criteria

Each configured supplier can return real candidate listings through its adapter. Results are normalized, timestamped, matched, and passed to the existing profit calculator.

---

## Phase 12 — Background processing, reliability, and performance

**Objective:** Make scans reliable at larger product volumes.

### 12.1 Job processing

Use persistent background workers. Do not keep a scan running inside a frontend request.

Support:
- Queueing.
- Concurrency limits.
- Retry with exponential backoff.
- Job timeouts.
- Cancellation.
- Worker crash recovery.
- Idempotent processing.
- Partial result persistence.

### 12.2 Progress counters

Track:
- Products discovered.
- Supplier searches attempted/completed.
- Candidate listings found.
- Matches accepted.
- AI verifications attempted/completed.
- Rejected candidates.
- Manual-review candidates.
- Profitable products.
- Errors and retries.

### 12.3 User experience

- Display progress from persisted worker events.
- Allow users to view partial results during a scan.
- Allow cancellation.
- Keep completed results if a later step fails.
- Explain partial completion and provider errors.

### 12.4 Performance

Implement:
- Database indexes.
- Server-side pagination.
- Bounded concurrency.
- Provider-specific rate limits.
- Search and match caching.
- AI response caching.
- Duplicate product detection.
- Incremental writes.
- Efficient export generation.

Do not promise scan duration until measured against real provider latency, quotas, and product counts.

### Acceptance criteria

Scans can run asynchronously, update progress accurately, survive transient failures, be cancelled safely, and preserve partial results.

---

## Phase 13 — Security, testing, deployment, and launch

**Objective:** Prepare the application for real users.

### 13.1 Security

- Keep all provider and DeepSeek keys server-side.
- Enforce authentication and authorization.
- Apply Supabase RLS.
- Validate and sanitize all inputs.
- Protect against server-side request forgery when accepting URLs.
- Rate-limit scan creation and expensive endpoints.
- Protect private exports.
- Avoid logging secrets or sensitive tokens.
- Use HTTPS in production.
- Validate file uploads and restrict size/type.
- Apply appropriate retention policies.

### 13.2 Automated testing

Test:
- Authentication and access control.
- Database migrations.
- Product normalization.
- Exact identifier matching.
- Candidate ranking.
- AI response parsing.
- AI timeout and failure handling.
- Profit formulas.
- Missing fee handling.
- Fee profile behavior.
- Best fulfillment selection.
- Scan lifecycle and cancellation.
- Worker retry/recovery.
- CSV export.
- Excel export.
- Provider rate limiting and errors.
- Demo/live separation.

### 13.3 Monitoring

Track:
- API errors and latency.
- Failed and partial scans.
- Worker health.
- Provider response times.
- Provider quota/rate-limit events.
- DeepSeek usage and estimated cost.
- Matching accuracy and manual-review rate.
- Cache hit rate.
- Scan duration.
- Export failures.

### 13.4 Deployment

Suggested arrangement:

| Service | Deployment |
|---|---|
| Frontend | Vercel |
| FastAPI backend | Persistent hosting |
| Background worker | Persistent hosting |
| Redis | Managed Redis |
| PostgreSQL/Auth | Supabase |
| Secrets | Hosting environment variables / secret manager |

The API and worker must be deployed as persistent services. A static frontend host alone is not sufficient.

### 13.5 Launch checklist

- Production environment variables configured.
- Database migrations applied.
- RLS policies verified.
- Demo Mode working.
- Live providers tested individually.
- Background worker monitored.
- Backups and recovery strategy configured.
- Error monitoring enabled.
- Privacy policy and terms reviewed.
- Provider terms and data rights reviewed.
- End-to-end acceptance tests passed.

### Acceptance criteria

A production deployment passes the critical end-to-end workflow and security tests. Known limitations are documented rather than hidden.

---

# 5. Post-MVP roadmap

Do not delay the first working release for these features. Consider them after validating the core product.

## 5.1 Product watchlist

Allow users to save opportunities and revisit them later.

## 5.2 Price history

Track historical Amazon and supplier prices when provider permissions and data retention terms allow it.

## 5.3 Automated rescanning

Allow scheduled rechecks of saved products.

## 5.4 Opportunity alerts

Notify users when a saved product reaches a target ROI, margin, or profit.

## 5.5 Bulk ASIN import

Allow users to upload CSV files containing ASINs and run individual-product sourcing in bulk.

## 5.6 Saved scan configurations

Save preferred categories, suppliers, filters, and fee profiles.

## 5.7 Exclusion rules

Allow users to exclude:
- Brands.
- Keywords.
- Categories.
- Suppliers.
- Product types.
- Specific ASINs.

## 5.8 Competition analysis

Add seller count, offer count, or other competition metrics only when the configured data source supports them reliably.

## 5.9 Advanced supplier comparison

Compare multiple supplier offers for the same Amazon product, including shipping, availability, variants, and landed cost.

---

# 6. Development milestones and release gates

| Milestone | Phases | Expected outcome |
|---|---:|---|
| A — Foundation | 1–2 | Application runs with database and core pages |
| B — Functional sourcing prototype | 3–4 | Complete simulated sourcing scan |
| C — Core intelligence | 5–7 | Matching, AI verification, and profit calculations |
| D — Usable research workflow | 8–9 | Results management and reliable exports |
| E — Live data | 10–11 | Authorized Amazon and supplier integrations |
| F — Production launch | 12–13 | Reliable background processing, security, deployment |

### Recommended first release gate

Do not pay for multiple marketplace providers until Milestone D is complete.

At that point, CommerceQuarry should already be able to:
- Accept a sourcing request.
- Discover sample Amazon products.
- Find sample supplier candidates.
- Match and reject products appropriately.
- Calculate all four fulfillment methods.
- Filter and sort opportunities.
- Export CSV and Excel files.

---

# 7. Antigravity development protocol

Use this document as the master specification. Implement one phase at a time.

## 7.1 Rules for the coding agent

1. Inspect the existing repository before changing files.
2. Preserve working code and explain any major architectural changes.
3. Follow phases in order.
4. Implement functionality rather than only writing plans or placeholder components.
5. Do not claim a feature works unless it has been run and tested.
6. Do not fake live marketplace integrations.
7. Use Demo Mode to exercise the real application services.
8. Keep API keys and secrets on the backend.
9. Add tests alongside each feature.
10. Update `IMPLEMENTATION_STATUS.md` after every phase.
11. Do not silently skip failed tests.
12. Ask for credentials only when a phase genuinely requires them; continue with mocks or Demo Mode where possible.
13. Do not begin the next phase until the current phase meets its acceptance criteria, unless a dependency or blocker is documented.

## 7.2 Required phase report

At the end of each phase, report:

- Phase number and name.
- Files created.
- Files modified.
- Database migrations added.
- Features actually implemented.
- Commands used to run the application.
- Tests executed and their results.
- Screens or endpoints verified.
- Known bugs and incomplete work.
- External credentials or configuration still required.
- Whether the acceptance criteria passed.

## 7.3 Project status file

Maintain `IMPLEMENTATION_STATUS.md` with:
- Current phase.
- Phase status: not started, in progress, blocked, or complete.
- Completed tasks.
- Outstanding tasks.
- Test results.
- Known issues.
- Next authorized phase.

## 7.4 Initial instruction

**Start with Phase 1 only.** Inspect the existing project, implement the foundation, run the frontend/backend/database checks, test the background worker, and report actual results. Do not merely repeat this plan or produce another planning document. Do not proceed to Phase 2 until Phase 1 acceptance criteria pass.

---

# 8. Final product acceptance test

The application is not considered MVP-complete until a user can:

1. Open CommerceQuarry and access the dashboard.
2. Start a Demo Mode category scan.
3. See the scan queued and running.
4. See progress counters update.
5. View discovered Amazon sample products.
6. View supplier candidates from the four simulated suppliers.
7. See exact, likely, rejected, and manual-review matches.
8. Open a product and inspect the comparison and match explanation.
9. See FBA, FBM, WFS, and Walmart Seller-Fulfilled profitability.
10. Change fee profiles and see calculations update correctly.
11. Filter and sort scan results.
12. Accept or reject a manual-review match.
13. Export filtered results to CSV.
14. Export a multi-sheet Excel workbook.
15. Open scan history and revisit completed results.
16. Cancel an active scan.
17. See simulated data clearly distinguished from live data.
18. Use the app without any paid marketplace provider credentials.

Only after this acceptance test passes should live marketplace integrations become the primary development focus.

**End of master implementation plan.**
