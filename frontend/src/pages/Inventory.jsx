import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Inventory() {
  const [data, setData] = useState(null)
  const [impact, setImpact] = useState(null)
  const [loading, setLoading] = useState(true)
  const [incompatibleOnly, setIncompatibleOnly] = useState(false)

  useEffect(() => {
    Promise.all([
      api.getInventory('?' + new URLSearchParams({ limit: 200, incompatible_only: incompatibleOnly }).toString()),
      api.getInventoryImpact(),
    ])
      .then(([d, i]) => { setData(d); setImpact(i) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [incompatibleOnly])

  if (loading) return <LoadingSpinner label="Loading inventory..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Inventory Impact Analysis</h2>
        <p className="text-slate-500 mt-1">Track inventory lots affected by anomalies</p>
      </div>

      {/* Impact summary */}
      {impact && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {impact.by_alarm_type.map((d) => (
            <div key={d.alarm_type} className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
              <div className="text-xs text-slate-500">{d.alarm_type.replace(/_/g, ' ')}</div>
              <div className="text-xl font-bold text-slate-800 mt-1">{d.lot_count}</div>
              <div className="text-xs text-slate-400">affected lots</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={incompatibleOnly} onChange={(e) => setIncompatibleOnly(e.target.checked)}
            className="rounded" />
          Show incompatible zone assignments only
        </label>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Product</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Category</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Zone</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Zone Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Qty</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Batch</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Arrival</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.data?.map((lot) => (
                <tr key={lot.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{lot.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">{lot.product_name}</td>
                  <td className="px-4 py-3 text-slate-600">{lot.product_category}</td>
                  <td className="px-4 py-3 text-slate-700">{lot.zone_name || lot.zone_id}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${incompatibleOnly ? 'bg-red-50 text-red-600' : 'bg-slate-100 text-slate-600'}`}>
                      {lot.zone_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{lot.quantity}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{lot.batch_number}</td>
                  <td className="px-4 py-3"><StatusBadge status={lot.status} /></td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{lot.arrival_date?.substring(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {data && <p className="text-sm text-slate-500">Showing {data.data.length} of {data.total} lots</p>}
    </div>
  )
}
