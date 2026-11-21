import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [status, setStatus] = useState<{database: string; redis: string} | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const resp = await fetch('/api/status');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        setStatus(data);
      } catch (e) {
        setError(String(e));
      }
    };
    fetchStatus();
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      {error && <p className="text-red-600">Error: {error}</p>}
      {status ? (
        <ul>
          <li>Database: <span className={status.database === 'ok' ? 'text-green-600' : 'text-red-600'}>{status.database}</span></li>
          <li>Redis: <span className={status.redis === 'ok' ? 'text-green-600' : 'text-red-600'}>{status.redis}</span></li>
        </ul>
      ) : (
        <p>Loading status...</p>
      )}
    </div>
  );
}
