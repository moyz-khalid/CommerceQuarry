import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="border-b pb-6">
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
          Welcome to CommerceQuarry
        </h1>
        <p className="text-gray-600 mt-1">
          Automated retail arbitrage research platform connecting Walmart seller storefronts to Home Depot, Lowe&apos;s, and AliExpress.
        </p>
      </div>

      {/* Hero Action: Seller Research */}
      <div className="p-6 bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-1">
          <span className="text-xs bg-blue-500/30 text-blue-300 px-2.5 py-1 rounded-full font-bold border border-blue-400/30 uppercase tracking-wider">
            ⭐ Primary Feature
          </span>
          <h2 className="text-2xl font-bold mt-2">Walmart Seller Research</h2>
          <p className="text-sm text-gray-300 max-w-xl">
            Paste any Walmart seller storefront URL to automatically uncover their catalog, identify equivalent supplier products, verify matches, and compute net profit margins.
          </p>
        </div>
        <Link
          href="/seller-research"
          className="px-6 py-3 bg-blue-500 hover:bg-blue-400 text-white font-bold rounded-xl transition shadow text-sm whitespace-nowrap"
        >
          Launch Seller Research →
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2">
        {[
          { href: '/seller-research', label: '⭐ Seller Research', desc: 'Scan Walmart storefronts & find supplier deals.' },
          { href: '/dashboard', label: 'Dashboard', desc: 'View system status, health, and aggregate metrics.' },
          { href: '/scan-results', label: 'Scan Results & Workspace', desc: 'Inspect side-by-side matches and export XLSX.' },
          { href: '/new-scan', label: 'Standard Catalog Scan', desc: 'Category and ASIN sourcing modes.' },
          { href: '/scan-history', label: 'Scan History', desc: 'Review past sourcing scans and progress logs.' },
          { href: '/fee-profiles', label: 'Fee Profiles', desc: 'Manage Walmart WFS and Seller-Fulfilled costs.' },
          { href: '/integrations', label: 'Integrations', desc: 'Configure SerpApi, Apify, and DeepSeek keys.' },
          { href: '/settings', label: 'Settings', desc: 'Adjust default parameters and rate limits.' },
        ].map(({ href, label, desc }) => (
          <Link
            key={href}
            href={href}
            className="block p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition border hover:border-blue-300"
          >
            <h2 className="font-semibold text-blue-700 mb-1">{label}</h2>
            <p className="text-xs text-gray-500">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
