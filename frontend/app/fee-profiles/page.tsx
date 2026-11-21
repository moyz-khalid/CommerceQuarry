"use client";
import React, { useEffect, useState } from "react";

interface FeeProfile {
  id: string;
  name: string;
  description?: string;
  fulfillment_method: string;
  is_default: boolean;
  is_enabled: boolean;
  referral_fee_pct: number;
  fulfillment_fee_flat: number;
  inbound_shipping_per_lb: number;
  prep_cost_per_unit: number;
  packaging_cost_per_unit: number;
  storage_fee_monthly_per_cuft: number;
  handling_per_order: number;
  misc_overhead_flat: number;
  created_at: string;
}

const METHODS = [
  { id: "amazon_fba", label: "Amazon FBA" },
  { id: "amazon_fbm", label: "Amazon FBM" },
  { id: "walmart_wfs", label: "Walmart WFS" },
  { id: "walmart_sf", label: "Walmart Seller-Fulfilled" },
];

export default function FeeProfilesPage() {
  const [profiles, setProfiles] = useState<FeeProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [method, setMethod] = useState("amazon_fba");
  const [referralPct, setReferralPct] = useState("15.0");
  const [fulfillmentFee, setFulfillmentFee] = useState("3.50");
  const [inboundShipping, setInboundShipping] = useState("0.45");
  const [prepCost, setPrepCost] = useState("1.00");
  const [packagingCost, setPackagingCost] = useState("0.50");
  const [storageFee, setStorageFee] = useState("0.87");
  const [handlingFee, setHandlingFee] = useState("0.25");
  const [overhead, setOverhead] = useState("0.25");
  const [isDefault, setIsDefault] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/fee-profiles", {
        headers: { Authorization: "Bearer demo-user" },
      });
      if (r.ok) {
        setProfiles(await r.json());
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    setError("");
    try {
      const r = await fetch("/api/fee-profiles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer demo-user",
        },
        body: JSON.stringify({
          name,
          description,
          fulfillment_method: method,
          referral_fee_pct: parseFloat(referralPct) || 15.0,
          fulfillment_fee_flat: parseFloat(fulfillmentFee) || 0.0,
          inbound_shipping_per_lb: parseFloat(inboundShipping) || 0.0,
          prep_cost_per_unit: parseFloat(prepCost) || 0.0,
          packaging_cost_per_unit: parseFloat(packagingCost) || 0.0,
          storage_fee_monthly_per_cuft: parseFloat(storageFee) || 0.0,
          handling_per_order: parseFloat(handlingFee) || 0.0,
          misc_overhead_flat: parseFloat(overhead) || 0.0,
          is_default: isDefault,
        }),
      });

      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to create profile (HTTP ${r.status})`);
      }

      setMsg("Fee profile created successfully!");
      setShowCreate(false);
      setName("");
      setDescription("");
      load();
    } catch (err: any) {
      setError(err.message || String(err));
    }
  };

  const handleDuplicate = async (id: string) => {
    try {
      const r = await fetch(`/api/fee-profiles/${id}/duplicate`, {
        method: "POST",
        headers: { Authorization: "Bearer demo-user" },
      });
      if (r.ok) {
        setMsg("Profile duplicated successfully!");
        load();
      }
    } catch (err: any) {
      setError(err.message || String(err));
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      const r = await fetch(`/api/fee-profiles/${id}/set-default`, {
        method: "POST",
        headers: { Authorization: "Bearer demo-user" },
      });
      if (r.ok) {
        setMsg("Default profile updated!");
        load();
      }
    } catch (err: any) {
      setError(err.message || String(err));
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this fee profile?")) return;
    try {
      const r = await fetch(`/api/fee-profiles/${id}`, {
        method: "DELETE",
        headers: { Authorization: "Bearer demo-user" },
      });
      if (r.ok) {
        setMsg("Profile deleted.");
        load();
      }
    } catch (err: any) {
      setError(err.message || String(err));
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fee Profiles</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure fulfillment fee schedules, shipping, packaging, and prep costs for accurate P&L calculations.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition"
        >
          {showCreate ? "Cancel" : "+ New Fee Profile"}
        </button>
      </div>

      {msg && <div className="p-3 bg-green-50 text-green-700 border border-green-200 rounded mb-4 text-sm">{msg}</div>}
      {error && <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded mb-4 text-sm">{error}</div>}

      {/* Create Profile Modal / Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white border rounded-lg p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-800">Create Fee Profile</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Profile Name</label>
              <input
                className="w-full border rounded px-3 py-1.5 text-sm"
                placeholder="e.g. Amazon FBA Standard Heavy"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Fulfillment Method</label>
              <select
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              >
                {METHODS.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Description (Optional)</label>
              <input
                className="w-full border rounded px-3 py-1.5 text-sm"
                placeholder="Notes or warehouse reference"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Referral Fee %</label>
              <input
                type="number"
                step="0.1"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={referralPct}
                onChange={(e) => setReferralPct(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Base Fulfillment Fee ($)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={fulfillmentFee}
                onChange={(e) => setFulfillmentFee(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Inbound Shipping ($/lb)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={inboundShipping}
                onChange={(e) => setInboundShipping(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Prep Cost ($/unit)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={prepCost}
                onChange={(e) => setPrepCost(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Packaging ($/unit)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={packagingCost}
                onChange={(e) => setPackagingCost(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Monthly Storage ($/cu ft)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={storageFee}
                onChange={(e) => setStorageFee(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Labor / Handling ($/order)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={handlingFee}
                onChange={(e) => setHandlingFee(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Misc Overhead ($)</label>
              <input
                type="number"
                step="0.01"
                className="w-full border rounded px-3 py-1.5 text-sm"
                value={overhead}
                onChange={(e) => setOverhead(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 mb-4">
            <input
              type="checkbox"
              id="isDefault"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="isDefault" className="text-xs text-gray-700 cursor-pointer">
              Set as default profile for this fulfillment method
            </label>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              className="px-5 py-2 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700"
            >
              Save Profile
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded text-sm hover:bg-gray-200"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Profiles Table */}
      {loading ? (
        <div className="py-12 text-center text-gray-500">Loading fee profiles...</div>
      ) : profiles.length === 0 ? (
        <div className="py-12 text-center text-gray-500 border border-dashed rounded-lg bg-white">
          No profiles configured. Click "+ New Fee Profile" above.
        </div>
      ) : (
        <div className="overflow-x-auto bg-white border rounded-lg shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Profile Name</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Method</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">Referral %</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">Base Fee</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">Prep / Box</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-700">Inbound / lb</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Default</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {profiles.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{p.name}</div>
                    {p.description && <div className="text-xs text-gray-500">{p.description}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                      {p.fulfillment_method.toUpperCase().replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{p.referral_fee_pct}%</td>
                  <td className="px-4 py-3 text-right">${p.fulfillment_fee_flat.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">${(p.prep_cost_per_unit + p.packaging_cost_per_unit).toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">${p.inbound_shipping_per_lb.toFixed(2)}</td>
                  <td className="px-4 py-3 text-center">
                    {p.is_default ? (
                      <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full">
                        ★ Default
                      </span>
                    ) : (
                      <button
                        onClick={() => handleSetDefault(p.id)}
                        className="text-xs text-gray-400 hover:text-blue-600 underline"
                      >
                        Set Default
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleDuplicate(p.id)}
                        className="text-xs text-blue-600 hover:underline"
                        title="Duplicate profile"
                      >
                        Duplicate
                      </button>
                      <button
                        onClick={() => handleDelete(p.id)}
                        className="text-xs text-red-600 hover:underline"
                        title="Delete profile"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
