"use client";
import React, { useEffect, useState } from 'react';

interface Integration {
  id: string;
  name: string;
  config: Record<string, unknown>;
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const load = async () => {
    const r = await fetch('/api/integrations', { headers: { Authorization: 'Bearer demo-user' } });
    setIntegrations(await r.json());
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    setError('');
    const r = await fetch('/api/integrations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer demo-user' },
      body: JSON.stringify({ name, config: {} }),
    });
    if (!r.ok) { setError(`Failed: ${r.status}`); return; }
    setMsg('Integration created!');
    setName('');
    load();
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Integrations</h1>
      <form onSubmit={handleCreate} className="flex gap-2 mb-6">
        <input
          className="border rounded px-2 py-1 flex-1"
          placeholder="Integration name (e.g. Home Depot)"
          value={name}
          onChange={e => setName(e.target.value)}
          required
        />
        <button type="submit" className="px-4 py-1 bg-blue-600 text-white rounded">Add</button>
      </form>
      {msg && <p className="text-green-600 mb-2">{msg}</p>}
      {error && <p className="text-red-600 mb-2">{error}</p>}
      <table className="min-w-full border">
        <thead><tr className="bg-gray-200">
          <th className="p-2 border">ID</th>
          <th className="p-2 border">Name</th>
        </tr></thead>
        <tbody>
          {integrations.map(i => (
            <tr key={i.id} className="odd:bg-white even:bg-gray-50">
              <td className="p-2 border break-all text-xs">{i.id}</td>
              <td className="p-2 border">{i.name}</td>
            </tr>
          ))}
          {integrations.length === 0 && (
            <tr><td colSpan={2} className="p-4 text-center text-gray-500">No integrations yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
