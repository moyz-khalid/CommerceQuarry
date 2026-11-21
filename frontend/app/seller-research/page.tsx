"use client";
import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";

interface DemoSeller {
  seller_id: string;
  seller_name: string;
  storefront_url: string;
  product_count: number;
  rating: number;
  categories: string[];
  sample_products: string[];
  is_demo: boolean;
}

interface SellerInfo {
  valid: boolean;
  seller_id?: string | null;
  seller_name?: string | null;
  storefront_url: string;
  product_count?: number | null;
  rating?: number | null;
  error?: string | null;
  is_demo?: boolean;
}

const SUPPLIERS = [
  { id: "home_depot", label: "Home Depot", color: "text-orange-600 bg-orange-50 border-orange-200" },
  { id: "lowes", label: "Lowe's", color: "text-blue-600 bg-blue-50 border-blue-200" },
  { id: "aliexpress", label: "AliExpress", color: "text-red-600 bg-red-50 border-red-200" },
];

const PRESET_LIMITS = [25, 50, 100, 250, 500];

export default function SellerResearchPage() {
  const [activeTab, setActiveTab] = useState<"url" | "csv">("url");

  // Seller URL State
  const [urlInput, setUrlInput] = useState("");
  const [manualSellerId, setManualSellerId] = useState("");
  const [parsing, setParsing] = useState(false);
  const [sellerInfo, setSellerInfo] = useState<SellerInfo | null>(null);
  const [demoSellers, setDemoSellers] = useState<DemoSeller[]>([]);

  // Configuration State
  const [maxProducts, setMaxProducts] = useState(50);
  const [customLimit, setCustomLimit] = useState("");
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>(["home_depot", "lowes", "aliexpress"]);
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minProfit, setMinProfit] = useState("");
  const [minROI, setMinROI] = useState("");
  const [enableAI, setEnableAI] = useState(false);
  const [useCache, setUseCache] = useState(true);
  const [demoMode, setDemoMode] = useState(true);

  // CSV Upload State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [csvText, setCsvText] = useState<string | null>(null);
  const [csvPreviewCount, setCsvPreviewCount] = useState<number | null>(null);
  const [csvLoading, setCsvLoading] = useState(false);

  // Scan & Progress State
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [matched, setMatched] = useState(0);
  const [profitable, setProfitable] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const pollTimer = useRef<NodeJS.Timeout | null>(null);

  // Load available demo sellers on mount
  useEffect(() => {
    fetch("/api/walmart/demo-sellers")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setDemoSellers(data);
      })
      .catch(() => {});
  }, []);

  // Poll scan progress
  useEffect(() => {
    if (!scanId) return;
    if (["completed", "completed_with_errors", "failed", "cancelled"].includes(scanStatus)) {
      if (pollTimer.current) clearInterval(pollTimer.current);
      return;
    }

    pollTimer.current = setInterval(async () => {
      try {
        const resp = await fetch(`/api/scans/${scanId}/progress`, {
          headers: { Authorization: "Bearer demo-user" },
        });
        if (!resp.ok) return;
        const d = await resp.json();
        setScanStatus(d.status);
        setProgress(d.progress || 0);
        setTotal(d.total || 0);
        setMatched(d.matched || 0);
        setProfitable(d.profitable || 0);
      } catch (err) {
        // quiet retry
      }
    }, 1000);

    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [scanId, scanStatus]);

  // URL Parsing Handler
  const handleParseUrl = async (inputStr: string) => {
    const val = inputStr.trim();
    if (!val) {
      setSellerInfo(null);
      return;
    }

    setParsing(true);
    try {
      const resp = await fetch("/api/walmart/parse-seller-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url_or_id: val }),
      });
      const data: SellerInfo = await resp.json();
      setSellerInfo(data);
      if (data.valid && data.seller_id) {
        setManualSellerId(data.seller_id);
      }
    } catch (err) {
      setSellerInfo({
        valid: false,
        storefront_url: val,
        error: "Failed to validate storefront URL. You can enter the Seller ID manually.",
      });
    } finally {
      setParsing(false);
    }
  };

  const handleSelectDemoSeller = (seller: DemoSeller) => {
    setUrlInput(seller.storefront_url);
    setManualSellerId(seller.seller_id);
    setSellerInfo({
      valid: true,
      seller_id: seller.seller_id,
      seller_name: seller.seller_name,
      storefront_url: seller.storefront_url,
      product_count: seller.product_count,
      rating: seller.rating,
      is_demo: true,
    });
  };

  const toggleSupplier = (supId: string) => {
    setSelectedSuppliers((prev) =>
      prev.includes(supId) ? prev.filter((s) => s !== supId) : [...prev, supId]
    );
  };

  // CSV File Handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadedFile(file);
    setCsvLoading(true);
    setErrorMsg("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/walmart/upload-products-csv", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        setErrorMsg(data.detail || "Failed to parse CSV file.");
        setCsvPreviewCount(null);
      } else {
        setCsvText(data.raw_csv_text);
        setCsvPreviewCount(data.product_count);
      }
    } catch (err: any) {
      setErrorMsg("Error uploading CSV: " + (err.message || String(err)));
    } finally {
      setCsvLoading(false);
    }
  };

  // Start Scan Handler
  const handleStartResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setScanId(null);
    setScanStatus("");
    setProgress(0);
    setTotal(0);
    setMatched(0);
    setProfitable(0);

    const effectiveLimit = customLimit ? parseInt(customLimit, 10) || 50 : maxProducts;
    const targetSellerId = manualSellerId || sellerInfo?.seller_id || "101001";

    if (activeTab === "url" && !urlInput && !manualSellerId) {
      setErrorMsg("Please enter a Walmart seller storefront URL or manual Seller ID.");
      return;
    }

    if (activeTab === "csv" && !csvText) {
      setErrorMsg("Please upload a valid CSV catalog file before starting research.");
      return;
    }

    setSubmitting(true);

    const payload = {
      seller_id: activeTab === "url" ? targetSellerId : "csv_catalog",
      storefront_url: activeTab === "url" ? sellerInfo?.storefront_url || urlInput : "local://catalog.csv",
      provider: activeTab === "csv" ? "csv" : demoMode ? "demo" : "serpapi",
      max_products: effectiveLimit,
      suppliers: selectedSuppliers,
      fulfillment_methods: ["walmart_wfs", "walmart_sf"],
      min_selling_price: minPrice ? parseFloat(minPrice) : null,
      max_selling_price: maxPrice ? parseFloat(maxPrice) : null,
      min_profit: minProfit ? parseFloat(minProfit) : null,
      min_roi: minROI ? parseFloat(minROI) : null,
      enable_ai_verification: enableAI,
      use_cache: useCache,
      demo: demoMode,
      csv_text: activeTab === "csv" ? csvText : null,
    };

    try {
      const resp = await fetch("/api/walmart/seller-scan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer demo-user",
        },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();
      if (!resp.ok) {
        if (typeof data.detail === "string") setErrorMsg(data.detail);
        else if (Array.isArray(data.detail)) setErrorMsg(data.detail.map((x: any) => x.msg).join("; "));
        else setErrorMsg(JSON.stringify(data));
        return;
      }

      setScanId(data.id);
      setScanStatus(data.status);
    } catch (err: any) {
      setErrorMsg("Network error: " + (err.message || String(err)));
    } finally {
      setSubmitting(false);
    }
  };

  const progressPct = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="border-b pb-6">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🛒</span>
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              Walmart Seller Research
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Analyze any Walmart seller storefront and cross-reference inventory with Home Depot, Lowe&apos;s, and AliExpress for profitable retail arbitrage.
            </p>
          </div>
        </div>
      </div>

      {/* Input Mode Tabs */}
      <div className="flex border-b">
        <button
          type="button"
          onClick={() => setActiveTab("url")}
          className={`px-6 py-3 font-semibold text-sm border-b-2 transition ${
            activeTab === "url"
              ? "border-blue-600 text-blue-600 bg-blue-50/40"
              : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          🌐 Storefront URL &amp; Seller ID
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("csv")}
          className={`px-6 py-3 font-semibold text-sm border-b-2 transition ${
            activeTab === "csv"
              ? "border-blue-600 text-blue-600 bg-blue-50/40"
              : "border-transparent text-gray-500 hover:text-gray-800"
          }`}
        >
          📁 CSV Catalog Upload
        </button>
      </div>

      <form onSubmit={handleStartResearch} className="space-y-6">
        {activeTab === "url" && (
          <div className="bg-white border rounded-2xl p-6 shadow-sm space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-800 mb-1">
                Walmart Seller Storefront URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 border rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="https://www.walmart.com/seller/101001 or enter Seller ID..."
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value);
                  }}
                  onBlur={() => handleParseUrl(urlInput)}
                />
                <button
                  type="button"
                  onClick={() => handleParseUrl(urlInput)}
                  disabled={parsing || !urlInput}
                  className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-xl text-sm transition disabled:opacity-50"
                >
                  {parsing ? "Validating..." : "Identify"}
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-1.5">
                Example: <code className="bg-gray-100 px-1 py-0.5 rounded text-gray-600">https://www.walmart.com/seller/101001</code> or paste any Walmart marketplace URL.
              </p>
            </div>

            {/* Quick Demo Sellers */}
            {demoSellers.length > 0 && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                    <span>⚡ Quick Test with Verified Demo Sellers</span>
                  </span>
                  <span className="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-bold">
                    DEMO DATA
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {demoSellers.map((seller) => (
                    <button
                      key={seller.seller_id}
                      type="button"
                      onClick={() => handleSelectDemoSeller(seller)}
                      className={`text-left p-3 rounded-lg border transition ${
                        sellerInfo?.seller_id === seller.seller_id
                          ? "bg-blue-50 border-blue-400 shadow-sm"
                          : "bg-white hover:border-gray-300"
                      }`}
                    >
                      <div className="font-bold text-xs text-gray-900 truncate">
                        {seller.seller_name}
                      </div>
                      <div className="text-[11px] text-gray-500 mt-0.5 flex justify-between">
                        <span>ID: {seller.seller_id}</span>
                        <span>⭐ {seller.rating}</span>
                      </div>
                      <div className="text-[10px] text-blue-600 mt-1 font-medium truncate">
                        {seller.categories.join(", ")}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Seller Information Card */}
            {sellerInfo && (
              <div
                className={`p-4 rounded-xl border transition ${
                  sellerInfo.valid
                    ? "bg-emerald-50/70 border-emerald-200"
                    : "bg-amber-50/70 border-amber-200"
                }`}
              >
                {sellerInfo.valid ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                        <span className="font-bold text-emerald-900 text-sm">
                          {sellerInfo.seller_name || `Walmart Seller #${sellerInfo.seller_id}`}
                        </span>
                        {sellerInfo.is_demo && (
                          <span className="text-[10px] bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded">
                            DEMO SELLER
                          </span>
                        )}
                      </div>
                      {sellerInfo.product_count && (
                        <span className="text-xs font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
                          ~{sellerInfo.product_count} products listed
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-gray-600 pt-2 border-t border-emerald-200/50">
                      <div>
                        <span className="font-medium text-gray-400 block">Seller ID</span>
                        <span className="font-mono text-gray-800">{sellerInfo.seller_id}</span>
                      </div>
                      <div className="sm:col-span-2">
                        <span className="font-medium text-gray-400 block">Storefront Link</span>
                        <a
                          href={sellerInfo.storefront_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline truncate block"
                        >
                          {sellerInfo.storefront_url}
                        </a>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="text-amber-800 text-xs font-semibold">
                      ⚠ {sellerInfo.error || "Could not automatically resolve seller."}
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-700 mb-1">
                        Manual Seller ID Override
                      </label>
                      <input
                        type="text"
                        className="w-full border rounded-lg px-3 py-1.5 text-xs bg-white focus:ring-1 focus:ring-blue-500"
                        placeholder="Enter Seller ID directly (e.g. 101001)"
                        value={manualSellerId}
                        onChange={(e) => setManualSellerId(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* CSV Import Mode */}
        {activeTab === "csv" && (
          <div className="bg-white border rounded-2xl p-6 shadow-sm space-y-4">
            <label className="block text-sm font-bold text-gray-800">
              Upload Walmart Products CSV
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-blue-400 transition cursor-pointer">
              <input
                type="file"
                accept=".csv"
                id="csvInput"
                onChange={handleFileUpload}
                className="hidden"
              />
              <label htmlFor="csvInput" className="cursor-pointer block">
                <div className="text-4xl mb-2">📄</div>
                <p className="font-medium text-sm text-gray-800">
                  {uploadedFile ? uploadedFile.name : "Click to browse or drag and drop your CSV file"}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Supports headers: <code className="bg-gray-100 px-1 py-0.5 rounded">walmart_product_id, product_title, current_price, upc, brand</code>
                </p>
              </label>
            </div>

            {csvLoading && <p className="text-xs text-blue-600">Validating CSV rows...</p>}
            {csvPreviewCount !== null && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center justify-between">
                <span>✓ Successfully loaded {csvPreviewCount} Walmart products from CSV</span>
                <span className="text-[10px] bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded">Ready to Scan</span>
              </div>
            )}
          </div>
        )}

        {/* Scan Configuration Card */}
        <div className="bg-white border rounded-2xl p-6 shadow-sm space-y-6">
          <h2 className="text-base font-bold text-gray-900 border-b pb-3">
            Research &amp; Sourcing Parameters
          </h2>

          {/* Supplier Sources */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
              Cross-Reference Suppliers
            </label>
            <div className="flex flex-wrap gap-3">
              {SUPPLIERS.map((sup) => {
                const checked = selectedSuppliers.includes(sup.id);
                return (
                  <button
                    key={sup.id}
                    type="button"
                    onClick={() => toggleSupplier(sup.id)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold border transition flex items-center gap-2 ${
                      checked
                        ? `${sup.color} shadow-sm ring-2 ring-blue-500/20`
                        : "bg-gray-50 text-gray-400 border-gray-200"
                    }`}
                  >
                    <span>{checked ? "✓" : "+"}</span>
                    <span>{sup.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Max Products Limit */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">
              Maximum Products to Collect &amp; Match
            </label>
            <div className="flex flex-wrap items-center gap-2">
              {PRESET_LIMITS.map((limit) => (
                <button
                  key={limit}
                  type="button"
                  onClick={() => {
                    setMaxProducts(limit);
                    setCustomLimit("");
                  }}
                  className={`px-4 py-2 rounded-lg text-xs font-bold border transition ${
                    maxProducts === limit && !customLimit
                      ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                      : "bg-gray-50 text-gray-700 hover:bg-gray-100 border-gray-200"
                  }`}
                >
                  {limit} Items
                </button>
              ))}
              <div className="flex items-center gap-1.5 ml-2">
                <span className="text-xs text-gray-400">Custom:</span>
                <input
                  type="number"
                  min={1}
                  max={1000}
                  placeholder="e.g. 75"
                  className="w-24 border rounded-lg px-2.5 py-1.5 text-xs text-gray-800"
                  value={customLimit}
                  onChange={(e) => setCustomLimit(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Price & Profit Filters */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Min Walmart Price ($)
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="10.00"
                className="w-full border rounded-lg px-3 py-1.5 text-xs"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Max Walmart Price ($)
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="250.00"
                className="w-full border rounded-lg px-3 py-1.5 text-xs"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Min Potential Profit ($)
              </label>
              <input
                type="number"
                step="0.5"
                placeholder="5.00"
                className="w-full border rounded-lg px-3 py-1.5 text-xs"
                value={minProfit}
                onChange={(e) => setMinProfit(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Min ROI (%)
              </label>
              <input
                type="number"
                step="1"
                placeholder="20"
                className="w-full border rounded-lg px-3 py-1.5 text-xs"
                value={minROI}
                onChange={(e) => setMinROI(e.target.value)}
              />
            </div>
          </div>

          {/* Advanced Toggles */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-3 border-t">
            <label className="flex items-center gap-2 cursor-pointer p-2.5 rounded-lg border hover:bg-gray-50">
              <input
                type="checkbox"
                checked={enableAI}
                onChange={(e) => setEnableAI(e.target.checked)}
                className="rounded text-blue-600"
              />
              <div>
                <span className="text-xs font-bold text-gray-800 block">DeepSeek AI Match Check</span>
                <span className="text-[10px] text-gray-400">Verifies ambiguous title differences</span>
              </div>
            </label>

            <label className="flex items-center gap-2 cursor-pointer p-2.5 rounded-lg border hover:bg-gray-50">
              <input
                type="checkbox"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
                className="rounded text-blue-600"
              />
              <div>
                <span className="text-xs font-bold text-gray-800 block">Search Cached Records</span>
                <span className="text-[10px] text-gray-400">Saves provider API requests</span>
              </div>
            </label>

            <label className="flex items-center gap-2 cursor-pointer p-2.5 rounded-lg border hover:bg-gray-50 bg-amber-50/30 border-amber-200/60">
              <input
                type="checkbox"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="rounded text-amber-600"
              />
              <div>
                <span className="text-xs font-bold text-amber-900 block flex items-center gap-1">
                  <span>Demo Mode</span>
                  <span className="text-[9px] bg-amber-200 text-amber-800 px-1 py-0.2 rounded font-bold">
                    OFFLINE
                  </span>
                </span>
                <span className="text-[10px] text-amber-700">Realistic catalog, zero API keys required</span>
              </div>
            </label>
          </div>
        </div>

        {/* Submit Button & Actions */}
        <div className="flex items-center justify-between">
          <button
            type="submit"
            disabled={submitting}
            className="px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all text-sm flex items-center gap-2 disabled:opacity-50"
          >
            <span>{submitting ? "Initiating Research..." : "🚀 Start Walmart Seller Research"}</span>
          </button>

          {demoMode && (
            <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg font-medium">
              Running in Simulation Mode with realistic verified demo catalog.
            </span>
          )}
        </div>
      </form>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs font-medium">
          {errorMsg}
        </div>
      )}

      {/* Progress Card */}
      {scanId && (
        <div className="bg-white border rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    scanStatus === "completed"
                      ? "bg-emerald-500"
                      : scanStatus === "failed"
                      ? "bg-red-500"
                      : "bg-blue-500 animate-pulse"
                  }`}
                ></span>
                <h3 className="font-bold text-gray-900 text-sm">
                  Research Status:{" "}
                  <span className="uppercase text-blue-600">{scanStatus}</span>
                </h3>
              </div>
              <p className="text-xs text-gray-400 mt-0.5 font-mono">Scan ID: {scanId}</p>
            </div>

            {scanStatus === "completed" && (
              <Link
                href={`/scan-results?scan_id=${scanId}`}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition shadow-sm"
              >
                Inspect Results &amp; Workspace →
              </Link>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                scanStatus === "completed" ? "bg-emerald-500" : "bg-blue-600"
              }`}
              style={{ width: `${total > 0 ? progressPct : 15}%` }}
            ></div>
          </div>

          {/* Progress Counters */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 bg-gray-50 rounded-xl border">
              <span className="text-[11px] text-gray-400 block font-medium">Products Analyzed</span>
              <span className="text-lg font-bold text-gray-800">
                {progress} / {total || "..."}
              </span>
            </div>
            <div className="p-3 bg-gray-50 rounded-xl border">
              <span className="text-[11px] text-gray-400 block font-medium">Suppliers Queried</span>
              <span className="text-lg font-bold text-gray-800">
                {selectedSuppliers.length} Sources
              </span>
            </div>
            <div className="p-3 bg-blue-50 rounded-xl border border-blue-100">
              <span className="text-[11px] text-blue-500 block font-medium">Verified Matches</span>
              <span className="text-lg font-bold text-blue-700">{matched}</span>
            </div>
            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
              <span className="text-[11px] text-emerald-600 block font-medium">Profitable Deals</span>
              <span className="text-lg font-bold text-emerald-700">{profitable}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
