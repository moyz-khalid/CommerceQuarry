"""
Export service — exports scan results to CSV and Microsoft Excel (.xlsx) formats.

Phase 9: Full support for:
  - 22 detailed product, matching, fee, and profitability columns
  - Spreadsheet formula injection protection (escapes =, +, -, @, \\t, \\r)
  - 5 formatted Excel worksheets:
      1. Profitable Products
      2. All Matched Products
      3. Manual Review
      4. Rejected Matches
      5. Scan Summary
  - Styling: frozen header rows, table filters, currency & percent formats, auto-fit column widths
"""
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def sanitize_cell(val: Any) -> Any:
    """Protect against spreadsheet formula injection."""
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


EXPORT_COLUMNS = [
    ("ASIN", lambda r: sanitize_cell(r.get("asin") or "")),
    ("Product Title", lambda r: sanitize_cell(r.get("title") or "")),
    ("Amazon URL", lambda r: sanitize_cell(r.get("url") or "")),
    ("Amazon Price ($)", lambda r: float(r.get("amazon_price", 0) or 0)),
    ("Supplier Name", lambda r: sanitize_cell(r.get("supplier_name") or "Simulated Supplier")),
    ("Supplier Product Title", lambda r: sanitize_cell(r.get("supplier_title") or r.get("title") or "")),
    ("Supplier URL", lambda r: sanitize_cell(r.get("supplier_url") or "")),
    ("Supplier Price ($)", lambda r: float(r.get("profit", {}).get("supplier_cost", 0) or 0)),
    ("Match Confidence", lambda r: sanitize_cell(str(r.get("match", {}).get("confidence") or "").upper())),
    ("Match Type", lambda r: sanitize_cell(str(r.get("match", {}).get("match_type") or r.get("match", {}).get("match_method") or ""))),
    ("Match Explanation", lambda r: sanitize_cell(r.get("match", {}).get("explanation") or "")),
    ("Product Differences", lambda r: sanitize_cell("; ".join(r.get("match", {}).get("differences") or []))),
    ("Marketplace Fees ($)", lambda r: float(r.get("profit", {}).get("referral_fee", 0) or 0)),
    ("Fulfillment Fees ($)", lambda r: float(r.get("profit", {}).get("fba_fee", 0) or 0)),
    ("Other Costs ($)", lambda r: float(round(float(r.get("profit", {}).get("total_fees", 0) or 0) - float(r.get("profit", {}).get("referral_fee", 0) or 0) - float(r.get("profit", {}).get("fba_fee", 0) or 0), 2))),
    ("Net Profit ($)", lambda r: float(r.get("profit", {}).get("net_profit", 0) or 0)),
    ("ROI (%)", lambda r: float(r.get("profit", {}).get("roi_pct", 0) or 0)),
    ("Margin (%)", lambda r: float(r.get("profit", {}).get("margin_pct", 0) or 0)),
    ("Best Fulfillment Method", lambda r: sanitize_cell(str(r.get("profit", {}).get("best_fulfillment_method") or "amazon_fba").upper())),
    ("Availability", lambda r: "In Stock" if r.get("in_stock", True) else "Out of Stock"),
    ("Simulated", lambda r: "Yes" if r.get("simulated", True) else "No"),
    ("Data Source", lambda r: "Simulated Demo" if r.get("simulated", True) else "Live Integration"),
    ("Calculation Status", lambda r: sanitize_cell(str(r.get("profit", {}).get("calculation_status") or "verified").upper())),
    ("Scan Timestamp", lambda r: sanitize_cell(r.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))),
]


def export_scan_results_csv(results: List[Dict[str, Any]]) -> str:
    """Generate CSV string of scan results with formula injection escaping."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")

    # Header
    headers = [col[0] for col in EXPORT_COLUMNS]
    writer.writerow(headers)

    # Rows
    for r in results:
        row = []
        for col in EXPORT_COLUMNS:
            val = col[1](r)
            if isinstance(val, float):
                if "%" in col[0]:
                    row.append(f"{val:.1f}%")
                else:
                    row.append(f"{val:.2f}")
            else:
                row.append(str(val))
        writer.writerow(row)

    return output.getvalue()


def _format_worksheet(ws, title: str, results: List[Dict[str, Any]]) -> None:
    """Format an individual worksheet with headers, styling, numbers, and auto-filters."""
    ws.title = title

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")  # Navy
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border_side = Side(border_style="thin", color="E5E7EB")
    row_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")  # Light green
    red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")    # Light red

    headers = [col[0] for col in EXPORT_COLUMNS]
    ws.append(headers)
    ws.row_dimensions[1].height = 24

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for row_idx, r in enumerate(results, start=2):
        row_data = [col[1](r) for col in EXPORT_COLUMNS]
        ws.append(row_data)
        ws.row_dimensions[row_idx].height = 20

        is_profitable = bool(r.get("profit", {}).get("profitable", False))

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = row_border
            header_name = headers[col_idx - 1]

            if "($)" in header_name:
                cell.alignment = right_align
                cell.number_format = "$#,##0.00"
            elif "(%)" in header_name:
                cell.alignment = right_align
                cell.number_format = "0.0%"
                # convert to ratio for Excel percent display
                if isinstance(cell.value, (int, float)):
                    cell.value = cell.value / 100.0
            elif "Confidence" in header_name or "Status" in header_name or "Availability" in header_name:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

            if header_name == "Net Profit ($)":
                cell.fill = green_fill if is_profitable else red_fill

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    # Freeze header row & apply table filter
    ws.freeze_panes = "A2"
    if results:
        ws.auto_filter.ref = ws.dimensions


def _create_summary_sheet(ws, scan_id: str, results: List[Dict[str, Any]], scan_meta: Optional[Dict[str, Any]] = None) -> None:
    """Create the Scan Summary KPI sheet."""
    ws.title = "Scan Summary"
    ws.views.sheetView[0].showGridLines = True

    meta = scan_meta or {}
    total = len(results)
    matched = sum(1 for r in results if r.get("match", {}).get("matched"))
    profitable = sum(1 for r in results if r.get("profit", {}).get("profitable"))
    review_needed = sum(1 for r in results if r.get("match", {}).get("manual_review") or r.get("match", {}).get("final_decision") in ("review", "investigation"))
    rejected = sum(1 for r in results if r.get("match", {}).get("final_decision") == "rejected" or not r.get("match", {}).get("matched"))

    profits = [float(r.get("profit", {}).get("net_profit", 0) or 0) for r in results if r.get("profit", {}).get("profitable")]
    avg_profit = round(sum(profits) / len(profits), 2) if profits else 0.0

    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    label_font = Font(name="Calibri", size=11, bold=True, color="374151")
    val_font = Font(name="Calibri", size=11, bold=False, color="111827")
    fill_kpi = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")

    ws.append(["CommerceQuarry — Sourcing Scan Report"])
    ws.cell(row=1, column=1).font = title_font
    ws.append([])

    kpis = [
        ("Scan ID", scan_id or "N/A"),
        ("Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Total Products Scanned", total),
        ("Matched Candidates", matched),
        ("Profitable Opportunities", profitable),
        ("Items Requiring Manual Review", review_needed),
        ("Rejected Matches", rejected),
        ("Average Net Profit (Profitable)", f"${avg_profit:.2f}"),
    ]

    for label, val in kpis:
        row_idx = ws.max_row + 1
        ws.append([label, val])
        ws.cell(row=row_idx, column=1).font = label_font
        ws.cell(row=row_idx, column=1).fill = fill_kpi
        ws.cell(row=row_idx, column=2).font = val_font

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 40


def export_scan_results_xlsx(
    results: List[Dict[str, Any]],
    scan_id: str = "",
    scan_meta: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate professional formatted Excel workbook with worksheets:
      - Scan Results (all results, active default)
      - Profitable Products
      - All Matched Products
      - Manual Review
      - Rejected Matches
      - Scan Summary
    """
    wb = openpyxl.Workbook()

    # Default Active Sheet: All Scan Results
    ws_main = wb.active
    _format_worksheet(ws_main, "Scan Results", results)

    # 1. Profitable Products
    ws_prof = wb.create_sheet()
    profitable_items = [r for r in results if r.get("profit", {}).get("profitable") and r.get("match", {}).get("matched")]
    _format_worksheet(ws_prof, "Profitable Products", profitable_items)

    # 2. All Matched Products
    ws_matched = wb.create_sheet()
    matched_items = [r for r in results if r.get("match", {}).get("matched")]
    _format_worksheet(ws_matched, "All Matched Products", matched_items)

    # 3. Manual Review
    ws_review = wb.create_sheet()
    review_items = [
        r for r in results
        if r.get("match", {}).get("manual_review") or r.get("match", {}).get("final_decision") in ("review", "investigation")
    ]
    _format_worksheet(ws_review, "Manual Review", review_items)

    # 4. Rejected Matches
    ws_rejected = wb.create_sheet()
    rejected_items = [
        r for r in results
        if r.get("match", {}).get("final_decision") == "rejected" or not r.get("match", {}).get("matched")
    ]
    _format_worksheet(ws_rejected, "Rejected Matches", rejected_items)

    # 5. Scan Summary
    ws_summary = wb.create_sheet()
    _create_summary_sheet(ws_summary, scan_id, results, scan_meta)

    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()
