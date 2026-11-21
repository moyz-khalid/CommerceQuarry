import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-2">Welcome to CommerceQuarry</h1>
      <p className="text-gray-600 mb-6">Use the sidebar to navigate to any section.</p>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { href: '/dashboard', label: 'Dashboard', desc: 'View system status and metrics.' },
          { href: '/new-scan', label: 'New Scan', desc: 'Start a product sourcing scan.' },
          { href: '/scan-history', label: 'Scan History', desc: 'Review past scans.' },
          { href: '/scan-results', label: 'Scan Results', desc: 'Browse sourcing opportunities.' },
          { href: '/fee-profiles', label: 'Fee Profiles', desc: 'Manage fulfillment cost profiles.' },
          { href: '/integrations', label: 'Integrations', desc: 'Configure supplier integrations.' },
          { href: '/settings', label: 'Settings', desc: 'Set preferences and defaults.' },
        ].map(({ href, label, desc }) => (
          <Link
            key={href}
            href={href}
            className="block p-4 bg-white rounded shadow hover:shadow-md transition border"
          >
            <h2 className="font-semibold text-blue-700 mb-1">{label}</h2>
            <p className="text-sm text-gray-500">{desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
