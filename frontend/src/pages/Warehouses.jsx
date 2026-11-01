import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Warehouses() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getWarehouses('?limit=500')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner label="Loading warehouses..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Warehouses</h2>
        <p className="text-slate-500 mt-1">All monitored warehouse facilities</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.map((w) => (
          <div key={w.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-800">{w.name}</h3>
              <span className="text-xs text-slate-400">#{w.id}</span>
            </div>
            <div className="space-y-1 text-sm text-slate-600">
              <p>Location: {w.location}</p>
              <p>Area: {w.total_area_sqm.toLocaleString()} sqm</p>
              <p>Manager: {w.manager || 'N/A'}</p>
              <p>Zones: <span className="font-medium text-brand-600">{w.zone_count || 0}</span></p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
