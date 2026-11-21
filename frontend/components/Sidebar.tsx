"use client";
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navLinks = [
  { href: '/seller-research', label: '⭐ Seller Research', isPrimary: true },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/new-scan', label: 'New Product Scan' },
  { href: '/scan-results', label: 'Scan Results' },
  { href: '/scan-history', label: 'Scan History' },
  { href: '/fee-profiles', label: 'Fee Profiles' },
  { href: '/integrations', label: 'Integrations' },
  { href: '/settings', label: 'Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="h-screen w-56 bg-gray-900 text-white flex flex-col p-4 fixed top-0 left-0 z-10 shadow-lg">
      <div className="mb-6">
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <span>CommerceQuarry</span>
        </h2>
        <p className="text-xs text-blue-400 font-medium mt-0.5">Walmart Sourcing Hub</p>
      </div>

      <nav className="flex flex-col space-y-1.5 flex-1">
        {navLinks.map(({ href, label, isPrimary }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-between ${
                isActive
                  ? isPrimary
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-gray-800 text-white'
                  : isPrimary
                  ? 'bg-blue-950/60 text-blue-300 hover:bg-blue-900/80 border border-blue-800/50'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span>{label}</span>
              {isPrimary && !isActive && (
                <span className="text-[10px] bg-blue-500/30 text-blue-300 px-1.5 py-0.5 rounded border border-blue-400/30 font-semibold">
                  MAIN
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="pt-4 border-t border-gray-800 text-[11px] text-gray-500 text-center">
        v2.0 • Walmart Research
      </div>
    </aside>
  );
}
