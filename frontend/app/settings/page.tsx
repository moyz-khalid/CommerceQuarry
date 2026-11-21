"use client";
import React, { useState } from 'react';

export default function SettingsPage() {
  const [defaultMode, setDefaultMode] = useState('category');
  const [maxProducts, setMaxProducts] = useState('100');
  const [minProfit, setMinProfit] = useState('5');
  const [minROI, setMinROI] = useState('20');
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: persist settings via API
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-8 max-w-lg">
      <h1 className="text-2xl font-bold mb-4">Settings</h1>
      <form onSubmit={handleSave} className="space-y-4">
        <label className="block">
          <span className="text-gray-700">Default Scan Mode</span>
          <select
            className="mt-1 block w-full border rounded px-2 py-1"
            value={defaultMode}
            onChange={e => setDefaultMode(e.target.value)}
          >
            <option value="category">Category</option>
            <option value="seller">Seller</option>
            <option value="product">Product (ASIN)</option>
          </select>
        </label>
        <label className="block">
          <span className="text-gray-700">Max Products per Scan</span>
          <input
            type="number"
            className="mt-1 block w-full border rounded px-2 py-1"
            value={maxProducts}
            onChange={e => setMaxProducts(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="text-gray-700">Minimum Net Profit ($)</span>
          <input
            type="number"
            className="mt-1 block w-full border rounded px-2 py-1"
            value={minProfit}
            onChange={e => setMinProfit(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="text-gray-700">Minimum ROI (%)</span>
          <input
            type="number"
            className="mt-1 block w-full border rounded px-2 py-1"
            value={minROI}
            onChange={e => setMinROI(e.target.value)}
          />
        </label>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
          Save Settings
        </button>
        {saved && <p className="text-green-600 inline ml-4">Saved!</p>}
      </form>
    </div>
  );
}
