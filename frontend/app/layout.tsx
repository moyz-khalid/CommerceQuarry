import React from 'react';
import './globals.css';
import Sidebar from '../components/Sidebar';

export const metadata = {
  title: 'CommerceQuarry',
  description: 'Product sourcing and profitability research platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-100 min-h-screen flex">
        <Sidebar />
        <main className="ml-56 flex-1 p-0">
          {children}
        </main>
      </body>
    </html>
  );
}
