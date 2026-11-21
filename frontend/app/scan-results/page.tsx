"use client";
import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";

interface MatchInfo {
  matched: boolean;
  confidence: string;
  score: number;
  match_method: string;
  mismatch_reason?: string;
  deterministic_score?: number;
  confidence_band?: string;
  match_type?: string;
  explanation?: string;
  differences?: string[];
  manual_review?: boolean;
  final_decision?: string;
  reviewer_decision?: string;
  reviewer_notes?: string;
  engine_version?: string;
  ai_verified?: boolean;
  ai_score?: number;
  ai_decision?: string;
  ai_reason?: string;
  ai_differences?: string[];
  tokens_used?: number;
  ai_cost_usd?: number;
}

interface ProfitInfo {
  profitable: boolean;
  net_profit: number;
  roi_pct: number;
  margin_pct: number;
  referral_fee: number;
  fba_fee: number;
  total_fees: number;
  total_cost: number;
  break_even_price: number;
  total_profit: number;
  supplier_cost?: number;
  simulated?: boolean;
  best_fulfillment_method?: string;
  calculation_status?: string;
  fulfillment_breakdown?: any;
  itemized_expenses?: any;
}

interface ScanResultItem {
  asin: string;
  title: string;
  brand?: string;
  amazon_price: number;
  url?: string;
  image_url?: string;
  upc?: string;
  mpn?: string;
  supplier_name?: string;
  supplier_title?: string;
  supplier_url?: string;
  supplier_image_url?: string;
  simulated: boolean;
  starred?: boolean;
  match: MatchInfo;
  profit: ProfitInfo;
  audit_trail?: Array<{
    timestamp: string;
    user_id: string;
    decision: string;
    notes?: string;
    corrected_price?: number;
    corrected_pack_count?: number;
  }>;
  corrected_price?: number;
  corrected_pack_count?: number;
}

interface ScanResultsResponse {
  scan_id: string;
  status: string;
  total_results: number;
  matched_count: number;
  profitable_count: number;
  review_count?: number;
  results: ScanResultItem[];
}

export default function ScanResultsPage() {
  const [scanId, setScanId] = useState<string | null>(null);
  const [data, setData] = useState<ScanResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "matched" | "profitable" | "review" | "starred">("all");
  const [supplierFilter, setSupplierFilter] = useState<string>("all");
  const [fulfillmentFilter, setFulfillmentFilter] = useState<string>("all");
  const [minProfit, setMinProfit] = useState<string>("");
  const [minRoi, setMinRoi] = useState<string>("");

  // Sorting
  const [sortBy, setSortBy] = useState<"net_profit" | "roi_pct" | "margin_pct" | "supplier_cost" | "amazon_price" | "score">("net_profit");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Interaction Modals & States
  const [selectedProduct, setSelectedProduct] = useState<ScanResultItem | null>(null);
  const [reviewingAsin, setReviewingAsin] = useState<string | null>(null);
  const [verifyingAiAsin, setVerifyingAiAsin] = useState<string | null>(null);

  // Modal review form
  const [modalDecision, setModalDecision] = useState<"accepted" | "rejected" | "investigation">("accepted");
  const [modalNotes, setModalNotes] = useState("");
  const [modalCorrectedPrice, setModalCorrectedPrice] = useState("");

  const loadResults = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/scans/${id}/results`, {
        headers: { Authorization: "Bearer demo-user" },
      });
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}));
        throw new Error(errBody.detail || `Failed to fetch results (HTTP ${resp.status})`);
      }
      const json: ScanResultsResponse = await resp.json();
      setData(json);
      setScanId(id);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const idFromUrl = params.get("scan_id");

    if (idFromUrl) {
      loadResults(idFromUrl);
    } else {
      fetch("/api/scans", {
        headers: { Authorization: "Bearer demo-user" },
      })
        .then((r) => r.json())
        .then((scans) => {
          if (Array.isArray(scans) && scans.length > 0) {
            const sorted = [...scans].sort(
              (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
            const latest = sorted[0];
            loadResults(latest.id);
          } else {
            setLoading(false);
          }
        })
        .catch((e) => {
          setError(String(e));
          setLoading(false);
        });
    }
  }, []);

  const handleToggleStar = async (asin: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!scanId) return;
    try {
      const resp = await fetch(`/api/scans/${scanId}/results/${asin}/star`, {
        method: "POST",
        headers: { Authorization: "Bearer demo-user" },
      });
      if (resp.ok) {
        const res = await resp.json();
        setData((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            results: prev.results.map((r) =>
              r.asin === asin ? { ...r, starred: res.starred } : r
            ),
          };
        });
        if (selectedProduct && selectedProduct.asin === asin) {
          setSelectedProduct((prev) => prev ? { ...prev, starred: res.starred } : null);
        }
      }
    } catch (err) {
      console.error("Failed to toggle star", err);
    }
  };

  const handleVerifyAI = async (asin: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!scanId) return;
    setVerifyingAiAsin(asin);
    try {
      const resp = await fetch(`/api/scans/${scanId}/results/${asin}/verify-ai`, {
        method: "POST",
        headers: { Authorization: "Bearer demo-user" },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "AI verification failed");
      }
      const updatedItem: ScanResultItem = await resp.json();
      setData((prev) => {
        if (!prev) return null;
        const newResults = prev.results.map((item) =>
          item.asin === asin ? updatedItem : item
        );
        return {
          ...prev,
          results: newResults,
          matched_count: newResults.filter((r) => r.match.matched).length,
          profitable_count: newResults.filter((r) => r.profit.profitable && r.match.matched).length,
        };
      });
      if (selectedProduct?.asin === asin) {
        setSelectedProduct(updatedItem);
      }
    } catch (e: any) {
      alert("AI Verification error: " + (e.message || String(e)));
    } finally {
      setVerifyingAiAsin(null);
    }
  };

  const handleReviewDecision = async (
    asin: string,
    decision: "accepted" | "rejected" | "investigation",
    notes?: string,
    correctedPrice?: number
  ) => {
    if (!scanId) return;
    setReviewingAsin(asin);
    try {
      const resp = await fetch(`/api/scans/${scanId}/results/${asin}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer demo-user",
        },
        body: JSON.stringify({
          decision,
          notes: notes || `Marked as ${decision} via Scan Results dashboard`,
          corrected_price: correctedPrice || undefined,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to update review decision");
      }

      const updatedItem: ScanResultItem = await resp.json();

      setData((prev) => {
        if (!prev) return null;
        const newResults = prev.results.map((item) =>
          item.asin === asin ? updatedItem : item
        );
        return {
          ...prev,
          results: newResults,
          matched_count: newResults.filter((r) => r.match.matched).length,
          profitable_count: newResults.filter((r) => r.profit.profitable && r.match.matched).length,
          review_count: newResults.filter(
            (r) => r.match.manual_review || r.match.final_decision in ["review", "investigation"]
          ).length,
        };
      });

      if (selectedProduct?.asin === asin) {
        setSelectedProduct(updatedItem);
      }
    } catch (err: any) {
      alert("Error saving review decision: " + (err.message || String(err)));
    } finally {
      setReviewingAsin(null);
    }
  };

  const handleExport = async (format: "csv" | "xlsx") => {
    if (!scanId) return;
    try {
      let exportUrl = `/api/scans/${scanId}/export?format=${format}`;
      if (filter === "profitable") exportUrl += "&profitable_only=true";
      if (filter === "starred") exportUrl += "&starred_only=true";
      if (supplierFilter !== "all") exportUrl += `&supplier=${supplierFilter}`;

      const resp = await fetch(exportUrl, {
        headers: { Authorization: "Bearer demo-user" },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Export failed (HTTP ${resp.status})`);
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scan_${scanId}_results.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert("Failed to export: " + (e.message || String(e)));
    }
  };

  const toggleSort = (field: "net_profit" | "roi_pct" | "margin_pct" | "supplier_cost" | "amazon_price" | "score") => {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
  };

  // Filtered & Sorted Display Items
  const displayedResults = useMemo(() => {
    if (!data?.results) return [];
    let items = [...data.results];

    // Status filter
    if (filter === "matched") {
      items = items.filter((r) => r.match.matched);
    } else if (filter === "profitable") {
      items = items.filter((r) => r.profit.profitable && r.match.matched);
    } else if (filter === "review") {
      items = items.filter(
        (r) => r.match.manual_review || r.match.final_decision === "review" || r.match.final_decision === "investigation"
      );
    } else if (filter === "starred") {
      items = items.filter((r) => r.starred);
    }

    // Supplier filter
    if (supplierFilter !== "all") {
      items = items.filter((r) => (r.supplier_name || "").toLowerCase().includes(supplierFilter.toLowerCase()));
    }

    // Fulfillment filter
    if (fulfillmentFilter !== "all") {
      items = items.filter((r) => (r.profit.best_fulfillment_method || "").toLowerCase() === fulfillmentFilter.toLowerCase());
    }

    // Numeric thresholds
    if (minProfit) {
      const val = parseFloat(minProfit);
      if (!isNaN(val)) items = items.filter((r) => r.profit.net_profit >= val);
    }
    if (minRoi) {
      const val = parseFloat(minRoi);
      if (!isNaN(val)) items = items.filter((r) => r.profit.roi_pct >= val);
    }

    // Keyword Search
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.asin.toLowerCase().includes(q) ||
          (r.brand && r.brand.toLowerCase().includes(q)) ||
          (r.supplier_title && r.supplier_title.toLowerCase().includes(q))
      );
    }

    // Sorting
    items.sort((a, b) => {
      let va = 0;
      let vb = 0;
      if (sortBy === "net_profit") {
        va = a.profit.net_profit;
        vb = b.profit.net_profit;
      } else if (sortBy === "roi_pct") {
        va = a.profit.roi_pct;
        vb = b.profit.roi_pct;
      } else if (sortBy === "margin_pct") {
        va = a.profit.margin_pct;
        vb = b.profit.margin_pct;
      } else if (sortBy === "supplier_cost") {
        va = a.profit.supplier_cost || 0;
        vb = b.profit.supplier_cost || 0;
      } else if (sortBy === "amazon_price") {
        va = a.amazon_price;
        vb = b.amazon_price;
      } else if (sortBy === "score") {
        va = a.match.score;
        vb = b.match.score;
      }
      return sortDir === "asc" ? va - vb : vb - va;
    });

    return items;
  }, [data, filter, supplierFilter, fulfillmentFilter, minProfit, minRoi, search, sortBy, sortDir]);

  const reviewCount = useMemo(() => {
    if (!data?.results) return 0;
    return data.results.filter(
      (r) => r.match.manual_review || r.match.final_decision === "review" || r.match.final_decision === "investigation"
    ).length;
  }, [data]);

  const starredCount = useMemo(() => {
    if (!data?.results) return 0;
    return data.results.filter((r) => r.starred).length;
  }, [data]);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Scan Results & Workspace</h1>
          {scanId && (
            <p className="text-xs text-gray-500 font-mono mt-1">Scan ID: {scanId}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {data && data.results.length > 0 && (
            <>
              <button
                onClick={() => handleExport("csv")}
                className="px-3 py-2 bg-emerald-600 text-white rounded text-sm font-medium hover:bg-emerald-700 transition flex items-center gap-1.5 shadow-sm"
              >
                <span>↓</span> Export CSV
              </button>
              <button
                onClick={() => handleExport("xlsx")}
                className="px-3 py-2 bg-emerald-700 text-white rounded text-sm font-medium hover:bg-emerald-800 transition flex items-center gap-1.5 shadow-sm"
              >
                <span>↓</span> Export Excel (5 Sheets)
              </button>
            </>
          )}
          <Link
            href="/new-scan"
            className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition"
          >
            + New Scan
          </Link>
          <Link
            href="/scan-history"
            className="px-4 py-2 bg-gray-100 text-gray-700 border rounded text-sm font-medium hover:bg-gray-200 transition"
          >
            Scan History
          </Link>
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-3 py-16 justify-center text-gray-500">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading scan results...</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm mb-6">
          <p className="font-semibold">Unable to load scan results</p>
          <p className="mt-1">{error}</p>
        </div>
      )}

      {!loading && !error && !data && (
        <div className="text-center py-16 bg-white border border-dashed rounded-lg text-gray-500">
          <p className="text-lg font-medium">No scan results found.</p>
          <p className="text-sm mt-1">
            Run a scan from the{" "}
            <Link href="/new-scan" className="text-blue-600 underline">
              New Scan
            </Link>{" "}
            page to view live opportunities.
          </p>
        </div>
      )}

      {!loading && data && (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Total Products
              </span>
              <p className="text-2xl font-bold text-gray-900 mt-1">{data.total_results}</p>
            </div>
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Matched
              </span>
              <p className="text-2xl font-bold text-blue-600 mt-1">{data.matched_count}</p>
            </div>
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Profitable
              </span>
              <p className="text-2xl font-bold text-emerald-600 mt-1">{data.profitable_count}</p>
            </div>
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Needs Review
              </span>
              <p className="text-2xl font-bold text-amber-600 mt-1">{reviewCount}</p>
            </div>
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">
                Starred
              </span>
              <p className="text-2xl font-bold text-yellow-500 mt-1">{starredCount}</p>
            </div>
          </div>

          {/* Interactive Filter & Search Bar */}
          <div className="bg-white border rounded-lg p-4 mb-6 shadow-sm flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="text"
                placeholder="🔍 Search title, ASIN, brand..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm w-full sm:w-64 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />

              <select
                value={supplierFilter}
                onChange={(e) => setSupplierFilter(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm bg-white"
              >
                <option value="all">All Suppliers</option>
                <option value="home_depot">Home Depot</option>
                <option value="walmart">Walmart</option>
                <option value="lowes">Lowe's</option>
                <option value="aliexpress">AliExpress</option>
              </select>

              <select
                value={fulfillmentFilter}
                onChange={(e) => setFulfillmentFilter(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm bg-white"
              >
                <option value="all">All Methods</option>
                <option value="amazon_fba">Amazon FBA</option>
                <option value="amazon_fbm">Amazon FBM</option>
                <option value="walmart_wfs">Walmart WFS</option>
                <option value="walmart_sf">Walmart SF</option>
              </select>

              <div className="flex items-center gap-1.5 text-xs text-gray-600">
                <span>Min $:</span>
                <input
                  type="number"
                  placeholder="0"
                  value={minProfit}
                  onChange={(e) => setMinProfit(e.target.value)}
                  className="w-16 px-2 py-1 border rounded text-xs"
                />
              </div>

              <div className="flex items-center gap-1.5 text-xs text-gray-600">
                <span>Min ROI %:</span>
                <input
                  type="number"
                  placeholder="0"
                  value={minRoi}
                  onChange={(e) => setMinRoi(e.target.value)}
                  className="w-16 px-2 py-1 border rounded text-xs"
                />
              </div>
            </div>

            {/* Quick Status Tabs */}
            <div className="flex flex-wrap gap-2 pt-2 border-t text-sm">
              {[
                { id: "all", label: "All Items" },
                { id: "profitable", label: "Profitable Only" },
                { id: "matched", label: "Matched Only" },
                { id: "review", label: `Manual Review (${reviewCount})` },
                { id: "starred", label: `★ Starred (${starredCount})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id as any)}
                  className={`px-3 py-1 rounded text-xs font-medium transition ${
                    filter === tab.id
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Results Table */}
          <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-600">
                <thead className="bg-gray-50 border-b text-gray-700 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-2 text-center w-8">★</th>
                    <th className="py-3 px-4">Product / ASIN</th>
                    <th
                      className="py-3 px-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleSort("amazon_price")}
                    >
                      Amazon Price {sortBy === "amazon_price" && (sortDir === "asc" ? "▲" : "▼")}
                    </th>
                    <th className="py-3 px-4">Supplier Candidate</th>
                    <th
                      className="py-3 px-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleSort("supplier_cost")}
                    >
                      Cost {sortBy === "supplier_cost" && (sortDir === "asc" ? "▲" : "▼")}
                    </th>
                    <th
                      className="py-3 px-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleSort("score")}
                    >
                      Confidence {sortBy === "score" && (sortDir === "asc" ? "▲" : "▼")}
                    </th>
                    <th
                      className="py-3 px-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleSort("net_profit")}
                    >
                      Net Profit {sortBy === "net_profit" && (sortDir === "asc" ? "▲" : "▼")}
                    </th>
                    <th
                      className="py-3 px-4 cursor-pointer hover:bg-gray-100"
                      onClick={() => toggleSort("roi_pct")}
                    >
                      ROI {sortBy === "roi_pct" && (sortDir === "asc" ? "▲" : "▼")}
                    </th>
                    <th className="py-3 px-4">Fulfillment</th>
                    <th className="py-3 px-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {displayedResults.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="py-8 text-center text-gray-500">
                        No products match the selected filters.
                      </td>
                    </tr>
                  ) : (
                    displayedResults.map((item) => {
                      const isReviewNeeded =
                        item.match.manual_review || item.match.final_decision in ["review", "investigation"];

                      return (
                        <tr
                          key={item.asin}
                          onClick={() => setSelectedProduct(item)}
                          className={`hover:bg-blue-50/50 cursor-pointer transition ${
                            isReviewNeeded ? "bg-amber-50/30" : ""
                          }`}
                        >
                          {/* Star toggle */}
                          <td className="py-3 px-2 text-center" onClick={(e) => handleToggleStar(item.asin, e)}>
                            <button
                              className={`text-base leading-none transition ${
                                item.starred ? "text-yellow-500 hover:text-yellow-600" : "text-gray-300 hover:text-gray-400"
                              }`}
                            >
                              ★
                            </button>
                          </td>

                          {/* Product Info */}
                          <td className="py-3 px-4 max-w-xs">
                            <p className="font-semibold text-gray-900 truncate" title={item.title}>
                              {item.title}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5 text-gray-500">
                              <span className="font-mono text-blue-600">{item.asin}</span>
                              {item.brand && <span>• {item.brand}</span>}
                              {item.upc && <span>• UPC: {item.upc}</span>}
                            </div>
                          </td>

                          {/* Amazon Price */}
                          <td className="py-3 px-4 font-mono font-medium text-gray-900">
                            ${item.amazon_price.toFixed(2)}
                          </td>

                          {/* Supplier Info */}
                          <td className="py-3 px-4 max-w-xs">
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">
                              {item.supplier_name || "Supplier"}
                            </span>
                            <p className="truncate text-gray-800 mt-0.5" title={item.supplier_title}>
                              {item.supplier_title || item.title}
                            </p>
                          </td>

                          {/* Supplier Cost */}
                          <td className="py-3 px-4 font-mono font-medium text-gray-900">
                            ${(item.profit.supplier_cost || 0).toFixed(2)}
                          </td>

                          {/* Match Confidence & AI Badge */}
                          <td className="py-3 px-4">
                            <div className="flex flex-col gap-1">
                              <span
                                className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase w-fit ${
                                  item.match.confidence === "exact"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : item.match.confidence === "high"
                                    ? "bg-blue-100 text-blue-800"
                                    : item.match.confidence === "medium"
                                    ? "bg-amber-100 text-amber-800"
                                    : "bg-red-100 text-red-800"
                                }`}
                              >
                                {item.match.confidence} ({(item.match.score * 100).toFixed(0)}%)
                              </span>
                              {item.match.ai_verified && (
                                <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold bg-purple-100 text-purple-800 w-fit">
                                  ✨ AI: {((item.match.ai_score || 0) * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Net Profit */}
                          <td className="py-3 px-4">
                            <span
                              className={`font-mono font-bold ${
                                item.profit.net_profit > 0 ? "text-emerald-600" : "text-red-600"
                              }`}
                            >
                              ${item.profit.net_profit.toFixed(2)}
                            </span>
                          </td>

                          {/* ROI */}
                          <td className="py-3 px-4 font-mono">
                            <span
                              className={item.profit.roi_pct > 0 ? "text-emerald-700 font-semibold" : "text-gray-500"}
                            >
                              {item.profit.roi_pct.toFixed(1)}%
                            </span>
                          </td>

                          {/* Best Fulfillment Method */}
                          <td className="py-3 px-4">
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-800 uppercase">
                              {item.profit.best_fulfillment_method || "amazon_fba"}
                            </span>
                          </td>

                          {/* Actions */}
                          <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-center gap-1.5">
                              {!item.match.ai_verified && (
                                <button
                                  onClick={(e) => handleVerifyAI(item.asin, e)}
                                  disabled={verifyingAiAsin === item.asin}
                                  className="px-2 py-1 text-[11px] bg-purple-600 text-white rounded hover:bg-purple-700 transition"
                                  title="Run DeepSeek AI verification"
                                >
                                  {verifyingAiAsin === item.asin ? "..." : "✨ AI"}
                                </button>
                              )}
                              <button
                                onClick={() => setSelectedProduct(item)}
                                className="px-2 py-1 text-[11px] bg-gray-100 text-gray-700 rounded border hover:bg-gray-200 transition"
                              >
                                Details
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Product Detail Modal */}
          {selectedProduct && (
            <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
              <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6">
                {/* Header */}
                <div className="flex justify-between items-start pb-4 border-b">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-blue-600">
                        {selectedProduct.asin}
                      </span>
                      <button
                        onClick={() => handleToggleStar(selectedProduct.asin)}
                        className={`text-lg leading-none ${
                          selectedProduct.starred ? "text-yellow-500" : "text-gray-300"
                        }`}
                      >
                        ★
                      </button>
                    </div>
                    <h2 className="text-lg font-bold text-gray-900 mt-1">
                      {selectedProduct.title}
                    </h2>
                  </div>
                  <button
                    onClick={() => setSelectedProduct(null)}
                    className="text-gray-400 hover:text-gray-600 text-xl font-bold p-1"
                  >
                    ✕
                  </button>
                </div>

                {/* Side-by-Side Product Comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-6">
                  {/* Amazon Box */}
                  <div className="border rounded-lg p-4 bg-orange-50/20">
                    <span className="text-xs font-bold text-orange-600 uppercase">Amazon Listing</span>
                    <p className="text-sm font-semibold text-gray-900 mt-1">{selectedProduct.title}</p>
                    <div className="mt-3 space-y-1 text-xs text-gray-600">
                      <p><span className="font-medium text-gray-800">Price:</span> ${selectedProduct.amazon_price.toFixed(2)}</p>
                      <p><span className="font-medium text-gray-800">Brand:</span> {selectedProduct.brand || "N/A"}</p>
                      <p><span className="font-medium text-gray-800">UPC:</span> {selectedProduct.upc || "N/A"}</p>
                      <p><span className="font-medium text-gray-800">MPN:</span> {selectedProduct.mpn || "N/A"}</p>
                      {selectedProduct.url && (
                        <p>
                          <a href={selectedProduct.url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                            View on Amazon ↗
                          </a>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Supplier Box */}
                  <div className="border rounded-lg p-4 bg-slate-50">
                    <span className="text-xs font-bold text-slate-700 uppercase">
                      Supplier Candidate ({selectedProduct.supplier_name || "Supplier"})
                    </span>
                    <p className="text-sm font-semibold text-gray-900 mt-1">
                      {selectedProduct.supplier_title || selectedProduct.title}
                    </p>
                    <div className="mt-3 space-y-1 text-xs text-gray-600">
                      <p><span className="font-medium text-gray-800">Cost:</span> ${(selectedProduct.profit.supplier_cost || 0).toFixed(2)}</p>
                      <p><span className="font-medium text-gray-800">Supplier:</span> {selectedProduct.supplier_name || "Unknown"}</p>
                      <p><span className="font-medium text-gray-800">Pack Count:</span> {selectedProduct.corrected_pack_count || 1}</p>
                      {selectedProduct.supplier_url && (
                        <p>
                          <a href={selectedProduct.supplier_url} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                            View on Supplier Site ↗
                          </a>
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Match Evaluation & AI Details */}
                <div className="border rounded-lg p-4 mb-6 bg-gray-50 text-xs">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold text-gray-800 uppercase tracking-wider">Matching Heuristics & Verification</span>
                    <span className="font-bold text-blue-600">
                      Score: {(selectedProduct.match.score * 100).toFixed(0)}% ({selectedProduct.match.confidence})
                    </span>
                  </div>
                  <p className="text-gray-700">
                    <span className="font-medium">Method:</span> {selectedProduct.match.match_method} •{" "}
                    <span className="font-medium">Decision:</span> {selectedProduct.match.final_decision}
                  </p>
                  {selectedProduct.match.explanation && (
                    <p className="mt-1 text-gray-600">{selectedProduct.match.explanation}</p>
                  )}
                  {selectedProduct.match.differences && selectedProduct.match.differences.length > 0 && (
                    <div className="mt-2 text-red-600">
                      <span className="font-semibold">Detected Differences:</span>
                      <ul className="list-disc list-inside mt-0.5">
                        {selectedProduct.match.differences.map((d, i) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* AI Verification Callout */}
                  {selectedProduct.match.ai_verified && (
                    <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded text-purple-900">
                      <div className="flex justify-between items-center font-bold">
                        <span>✨ DeepSeek AI Verification</span>
                        <span>Confidence: {((selectedProduct.match.ai_score || 0) * 100).toFixed(0)}%</span>
                      </div>
                      <p className="mt-1">{selectedProduct.match.ai_reason}</p>
                    </div>
                  )}
                </div>

                {/* Fulfillment Methods P&L Breakdown */}
                {selectedProduct.profit.fulfillment_breakdown && (
                  <div className="mb-6">
                    <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-3">
                      Fulfillment Method P&L Comparison
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      {Object.entries(selectedProduct.profit.fulfillment_breakdown).map(([mName, pnl]: [string, any]) => (
                        <div
                          key={mName}
                          className={`border rounded-lg p-3 ${
                            selectedProduct.profit.best_fulfillment_method === mName
                              ? "border-blue-500 bg-blue-50/30"
                              : "bg-white"
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <span className="font-bold uppercase text-[11px] text-gray-800">
                              {mName.replace("_", " ")}
                            </span>
                            {selectedProduct.profit.best_fulfillment_method === mName && (
                              <span className="text-[9px] bg-blue-600 text-white px-1 rounded">Best</span>
                            )}
                          </div>
                          <p className="text-lg font-bold mt-1 text-gray-900 font-mono">
                            ${pnl.net_profit.toFixed(2)}
                          </p>
                          <div className="space-y-0.5 mt-2 text-gray-600">
                            <p>ROI: {pnl.roi_pct.toFixed(1)}%</p>
                            <p>Margin: {pnl.margin_pct.toFixed(1)}%</p>
                            <p>Break-Even: ${pnl.break_even_price.toFixed(2)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Review Action & Corrections */}
                <div className="border-t pt-4">
                  <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-3">
                    Manual Review Decision & Corrections
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Decision</label>
                      <select
                        value={modalDecision}
                        onChange={(e) => setModalDecision(e.target.value as any)}
                        className="w-full px-2.5 py-1.5 border rounded text-xs bg-white"
                      >
                        <option value="accepted">Accept Match</option>
                        <option value="rejected">Reject Match</option>
                        <option value="investigation">Mark for Investigation</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Corrected Cost ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Leave blank to keep"
                        value={modalCorrectedPrice}
                        onChange={(e) => setModalCorrectedPrice(e.target.value)}
                        className="w-full px-2.5 py-1.5 border rounded text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Reviewer Notes</label>
                      <input
                        type="text"
                        placeholder="e.g. Verified packaging count"
                        value={modalNotes}
                        onChange={(e) => setModalNotes(e.target.value)}
                        className="w-full px-2.5 py-1.5 border rounded text-xs"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setSelectedProduct(null)}
                      className="px-3 py-1.5 border rounded text-xs text-gray-700 hover:bg-gray-100"
                    >
                      Close
                    </button>
                    <button
                      disabled={reviewingAsin === selectedProduct.asin}
                      onClick={() =>
                        handleReviewDecision(
                          selectedProduct.asin,
                          modalDecision,
                          modalNotes,
                          modalCorrectedPrice ? parseFloat(modalCorrectedPrice) : undefined
                        )
                      }
                      className="px-4 py-1.5 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {reviewingAsin === selectedProduct.asin ? "Saving..." : "Save Review Decision"}
                    </button>
                  </div>
                </div>

                {/* Audit Trail Log */}
                {selectedProduct.audit_trail && selectedProduct.audit_trail.length > 0 && (
                  <div className="border-t mt-4 pt-3 text-xs text-gray-500">
                    <span className="font-bold text-gray-700 block mb-1">Audit Trail:</span>
                    <ul className="space-y-1">
                      {selectedProduct.audit_trail.map((entry, idx) => (
                        <li key={idx} className="bg-gray-50 p-1.5 rounded">
                          <span className="font-semibold text-gray-700 uppercase">[{entry.decision}]</span>{" "}
                          by {entry.user_id} at {new Date(entry.timestamp).toLocaleString()} — {entry.notes}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
