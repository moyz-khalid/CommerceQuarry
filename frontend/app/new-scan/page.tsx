"use client";
import React, { useState, useEffect, useRef } from "react";

const SUPPLIERS = [
  { id: "home_depot", label: "Home Depot" },
  { id: "walmart", label: "Walmart" },
  { id: "lowes", label: "Lowe's" },
  { id: "aliexpress", label: "AliExpress" },
];
const FULFILLMENT = [
  { id: "amazon_fba", label: "Amazon FBA" },
  { id: "amazon_fbm", label: "Amazon FBM" },
  { id: "walmart_wfs", label: "Walmart WFS" },
  { id: "walmart_sf", label: "Walmart Seller-Fulfilled" },
];

interface Meta {
  categories: string[];
}

export default function NewScan() {
  const [meta, setMeta] = useState<Meta>({ categories: [] });
  const [mode, setMode] = useState("category");
  const [demo, setDemo] = useState(true);

  // Category config
  const [category, setCategory] = useState("");
  const [amazonMin, setAmazonMin] = useState("");
  const [amazonMax, setAmazonMax] = useState("");
  const [supplierMin, setSupplierMin] = useState("");
  const [supplierMax, setSupplierMax] = useState("");
  const [minProfit, setMinProfit] = useState("");
  const [minROI, setMinROI] = useState("");
  const [minMargin, setMinMargin] = useState("");
  const [maxProducts, setMaxProducts] = useState("100");
  const [suppliers, setSuppliers] = useState<string[]>(SUPPLIERS.map(s => s.id));
  const [fulfillments, setFulfillments] = useState<string[]>(FULFILLMENT.map(f => f.id));

  // Seller config
  const [sellerId, setSellerId] = useState("");
  const [storefrontUrl, setStorefrontUrl] = useState("");

  // Product config
  const [asin, setAsin] = useState("");
  const [productUrl, setProductUrl] = useState("");

  // Scan state
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string>("");
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [matched, setMatched] = useState(0);
  const [profitable, setProfitable] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetch("/api/scans/meta")
      .then(r => r.json())
      .then(d => { setMeta(d); if (d.categories.length) setCategory(d.categories[0]); })
      .catch(() => {});
  }, []);

  // Poll progress when scan is running
  useEffect(() => {
    if (!scanId) return;
    if (["completed", "completed_with_errors", "failed", "cancelled"].includes(scanStatus)) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`/api/scans/${scanId}/progress`, {
          headers: { Authorization: "Bearer demo-user" },
        });
        if (!r.ok) return;
        const d = await r.json();
        setScanStatus(d.status);
        setProgress(d.progress);
        setTotal(d.total);
        setMatched(d.matched);
        setProfitable(d.profitable);
        if (["completed", "completed_with_errors", "failed", "cancelled"].includes(d.status)) {
          clearInterval(pollRef.current!);
        }
      } catch {}
    }, 1000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [scanId, scanStatus]);

  const toggleSupplier = (id: string) =>
    setSuppliers(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  const toggleFulfillment = (id: string) =>
    setFulfillments(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);

  const buildPayload = () => {
    const base = { mode, demo };
    if (mode === "category") {
      return {
        ...base,
        category_config: {
          category,
          amazon_price_min: amazonMin ? parseFloat(amazonMin) : null,
          amazon_price_max: amazonMax ? parseFloat(amazonMax) : null,
          supplier_price_min: supplierMin ? parseFloat(supplierMin) : null,
          supplier_price_max: supplierMax ? parseFloat(supplierMax) : null,
          min_profit: minProfit ? parseFloat(minProfit) : null,
          min_roi: minROI ? parseFloat(minROI) : null,
          min_margin: minMargin ? parseFloat(minMargin) : null,
          max_products: parseInt(maxProducts, 10),
          suppliers,
          fulfillment_methods: fulfillments,
          demo,
        },
      };
    }
    if (mode === "seller") {
      return {
        ...base,
        seller_config: {
          seller_id: sellerId || null,
          storefront_url: storefrontUrl || null,
          max_products: parseInt(maxProducts, 10),
          suppliers,
          fulfillment_methods: fulfillments,
          demo,
        },
      };
    }
    return {
      ...base,
      product_config: {
        asin: asin || null,
        product_url: productUrl || null,
        suppliers,
        fulfillment_methods: fulfillments,
        demo,
      },
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setScanId(null); setScanStatus(""); setProgress(0);
    setSubmitting(true);
    try {
      const r = await fetch("/api/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer demo-user" },
        body: JSON.stringify(buildPayload()),
      });
      const d = await r.json();
      if (!r.ok) {
        // d.detail may be a string OR an array of Pydantic validation error objects
        if (typeof d.detail === "string") {
          setError(d.detail);
        } else if (Array.isArray(d.detail)) {
          setError(d.detail.map((e: any) => e.msg || JSON.stringify(e)).join("; "));
        } else {
          setError(JSON.stringify(d));
        }
        return;
      }
      setScanId(d.id);
      setScanStatus(d.status);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!scanId) return;
    await fetch(`/api/scans/${scanId}/cancel`, {
      method: "POST",
      headers: { Authorization: "Bearer demo-user" },
    });
    setScanStatus("cancelled");
  };

  const pct = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-1">New Product Scan</h1>
      {demo && (
        <div className="mb-4 px-3 py-1 bg-yellow-100 border border-yellow-300 text-yellow-800 rounded text-sm inline-block">
          Demo Mode — simulated data, no credentials required
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Mode & Demo */}
        <div className="flex items-center gap-6">
          <label className="block">
            <span className="text-gray-700 font-medium">Sourcing Mode</span>
            <select
              className="mt-1 block w-48 border rounded px-2 py-1"
              value={mode}
              onChange={e => setMode(e.target.value)}
            >
              <option value="category">Category</option>
              <option value="seller">Seller</option>
              <option value="product">Product (ASIN)</option>
            </select>
          </label>
          <label className="flex items-center gap-2 mt-5 cursor-pointer">
            <input type="checkbox" checked={demo} onChange={e => setDemo(e.target.checked)} />
            <span className="text-gray-700">Demo Mode</span>
          </label>
        </div>

        {/* Category Mode */}
        {mode === "category" && (
          <div className="space-y-3 border rounded p-4 bg-gray-50">
            <label className="block">
              <span className="text-sm font-medium">Amazon Category</span>
              <select
                className="mt-1 block w-full border rounded px-2 py-1"
                value={category}
                onChange={e => setCategory(e.target.value)}
                required
              >
                {meta.categories.map(c => <option key={c}>{c}</option>)}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-sm">Amazon Price Min ($)</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={amazonMin} onChange={e => setAmazonMin(e.target.value)} placeholder="0" />
              </label>
              <label className="block">
                <span className="text-sm">Amazon Price Max ($)</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={amazonMax} onChange={e => setAmazonMax(e.target.value)} placeholder="500" />
              </label>
              <label className="block">
                <span className="text-sm">Min Net Profit ($)</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={minProfit} onChange={e => setMinProfit(e.target.value)} placeholder="5" />
              </label>
              <label className="block">
                <span className="text-sm">Min ROI (%)</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={minROI} onChange={e => setMinROI(e.target.value)} placeholder="20" />
              </label>
              <label className="block">
                <span className="text-sm">Min Margin (%)</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={minMargin} onChange={e => setMinMargin(e.target.value)} placeholder="15" />
              </label>
              <label className="block">
                <span className="text-sm">Max Products</span>
                <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={maxProducts} onChange={e => setMaxProducts(e.target.value)} min={1} max={1000} required />
              </label>
            </div>
          </div>
        )}

        {/* Seller Mode */}
        {mode === "seller" && (
          <div className="space-y-3 border rounded p-4 bg-gray-50">
            <p className="text-xs text-blue-600 font-medium">ℹ️ Demo Mode uses simulated seller inventory. Enter any Seller ID or storefront URL to test.</p>
            <label className="block">
              <span className="text-sm font-medium">Amazon Seller ID</span>
              <input type="text" className="mt-1 block w-full border rounded px-2 py-1" value={sellerId} onChange={e => setSellerId(e.target.value)} placeholder="A1EXAMPLE123456" />
            </label>
            <label className="block">
              <span className="text-sm font-medium">or Storefront URL</span>
              <input type="url" className="mt-1 block w-full border rounded px-2 py-1" value={storefrontUrl} onChange={e => setStorefrontUrl(e.target.value)} placeholder="https://www.amazon.com/s?me=... or https://www.walmart.com/seller/..." />
              <span className="text-xs text-gray-400 mt-0.5 block">Supports Amazon and Walmart storefront URLs.</span>
            </label>
            <label className="block">
              <span className="text-sm">Max Products</span>
              <input type="number" className="mt-1 block w-full border rounded px-2 py-1" value={maxProducts} onChange={e => setMaxProducts(e.target.value)} min={1} max={1000} required />
            </label>
          </div>
        )}

        {/* Product Mode */}
        {mode === "product" && (
          <div className="space-y-3 border rounded p-4 bg-gray-50">
            <label className="block">
              <span className="text-sm font-medium">ASIN</span>
              <input type="text" className="mt-1 block w-full border rounded px-2 py-1 font-mono" value={asin} onChange={e => setAsin(e.target.value.toUpperCase())} placeholder="B0XXXXXXXXXX" maxLength={10} />
            </label>
            <label className="block">
              <span className="text-sm font-medium">or Amazon Product URL</span>
              <input type="url" className="mt-1 block w-full border rounded px-2 py-1" value={productUrl} onChange={e => setProductUrl(e.target.value)} placeholder="https://www.amazon.com/dp/B0XXXXXXXXXX" />
            </label>
          </div>
        )}

        {/* Supplier Selection */}
        <div className="border rounded p-4 bg-gray-50">
          <p className="text-sm font-medium mb-2">Supplier Marketplaces</p>
          <div className="flex flex-wrap gap-3">
            {SUPPLIERS.map(s => (
              <label key={s.id} className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={suppliers.includes(s.id)} onChange={() => toggleSupplier(s.id)} />
                <span className="text-sm">{s.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Fulfillment Methods */}
        <div className="border rounded p-4 bg-gray-50">
          <p className="text-sm font-medium mb-2">Fulfillment Methods</p>
          <div className="flex flex-wrap gap-3">
            {FULFILLMENT.map(f => (
              <label key={f.id} className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={fulfillments.includes(f.id)} onChange={() => toggleFulfillment(f.id)} />
                <span className="text-sm">{f.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex gap-3 items-center">
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2 bg-blue-600 text-white rounded font-medium disabled:opacity-50"
          >
            {submitting ? "Starting…" : "Start Scan"}
          </button>
          {scanId && ["queued", "running"].includes(scanStatus) && (
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 bg-red-500 text-white rounded"
            >
              Cancel Scan
            </button>
          )}
        </div>
      </form>

      {/* Progress / Result Panel */}
      {scanId && (
        <div className="mt-6 border rounded p-4 bg-white shadow-sm">
          <p className="font-semibold mb-2">
            Scan Status:{" "}
            <span className={
              scanStatus === "completed" ? "text-green-600" :
              scanStatus === "failed" || scanStatus === "cancelled" ? "text-red-600" :
              "text-blue-600"
            }>
              {scanStatus}
            </span>
          </p>
          {total > 0 && (
            <>
              <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                <div
                  className="bg-blue-500 h-3 rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-sm text-gray-600">
                {progress} / {total} products &nbsp;|&nbsp; {matched} matched &nbsp;|&nbsp; {profitable} profitable
              </p>
            </>
          )}
          <p className="text-xs text-gray-400 mt-2 font-mono">Scan ID: {scanId}</p>
          {scanStatus === "completed" && (
            <a href={`/scan-results?scan_id=${scanId}`} className="mt-3 inline-block px-4 py-1 bg-green-600 text-white rounded text-sm">
              View Results →
            </a>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-300 text-red-700 rounded text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
