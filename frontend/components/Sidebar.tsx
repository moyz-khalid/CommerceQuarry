import React from 'react';
import Link from 'next/link';

const navLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/new-scan', label: 'New Product Scan' },
  { href: '/scan-results', label: 'Scan Results' },
  { href: '/scan-history', label: 'Scan History' },
  { href: '/fee-profiles', label: 'Fee Profiles' },
  { href: '/integrations', label: 'Integrations' },
  { href: '/settings', label: 'Settings' },
];

export default function Sidebar() {
  return (
    <aside className="h-screen w-56 bg-gray-900 text-white flex flex-col p-4 fixed top-0 left-0 z-10">
      <h2 className="text-xl font-bold mb-8 tracking-tight">CommerceQuarry</h2>
      <nav className="flex flex-col space-y-1">
        {navLinks.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="px-3 py-2 rounded hover:bg-gray-700 transition-colors text-sm"
          >
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
