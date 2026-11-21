"use client";
import React, { useEffect, useState } from 'react';

interface Scan {
  id: string;
  user_id: string;
  mode: string;
  status: string;
  created_at: string;
}

export default function ScanHistory() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchScans = async () => {
      try {
        const resp = await fetch('/api/scans', {
          headers: { Authorization: 'Bearer demo-user' },
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        setScans(data);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    };
    fetchScans();
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Scan History</h1>
      {loading && <p>Loading scans...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <table className="min-w-full border">
          <thead>
            <tr className="bg-gray-200">
              <th className="p-2 border">ID</th>
              <th className="p-2 border">Mode</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Created At</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
              <tr key={s.id} className="odd:bg-white even:bg-gray-50">
                <td className="p-2 border break-all font-mono text-xs">{s.id}</td>
                <td className="p-2 border capitalize">{s.mode}</td>
                <td className="p-2 border">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    s.status === "completed" ? "bg-green-100 text-green-800" :
                    s.status === "failed" ? "bg-red-100 text-red-800" :
                    "bg-blue-100 text-blue-800"
                  }`}>
                    {s.status}
                  </span>
                </td>
                <td className="p-2 border text-sm">{new Date(s.created_at).toLocaleString()}</td>
                <td className="p-2 border">
                  {s.status === "completed" ? (
                    <a
                      href={`/scan-results?scan_id=${s.id}`}
                      className="text-blue-600 hover:underline text-sm font-medium"
                    >
                      View Results →
                    </a>
                  ) : (
                    <span className="text-gray-400 text-xs">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
