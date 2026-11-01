import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Sensors() {
  const [data, setData] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ status: '', sensor_type: '' })

  useEffect(() => {
    Promise.all([
      api.getSensors('?' + new URLSearchParams({ ...filters, limit: 500 }).toString()),
      api.getSensorHealth(),
    ])
      .then(([s, h]) => { setData(s); setHealth(h) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [filters])

  if (loading) return <LoadingSpinner label="Loading sensors..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Sensor Health Monitoring</h2>
        <p className="text-slate-500 mt-1">Track sensor status and availability</p>
      </div>

      {/* Health summary */}
      {health && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {health.by_status.map((s) => (
            <div key={s.status} className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <StatusBadge status={s.status} />
                <span className="text-2xl font-bold text-slate-800">{s.count}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="drift">Drift</option>
          <option value="offline">Offline</option>
        </select>
        <select value={filters.sensor_type} onChange={(e) => setFilters({ ...filters, sensor_type: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Types</option>
          <option value="temperature">Temperature</option>
          <option value="humidity">Humidity</option>
          <option value="occupancy">Occupancy</option>
          <option value="door">Door</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Zone</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Manufacturer</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Model</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Installed</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Calibrated</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Zone Mappings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{s.id}</td>
                  <td className="px-4 py-3 text-slate-700">{s.zone_id}</td>
                  <td className="px-4 py-3 text-slate-700">{s.sensor_type}</td>
                  <td className="px-4 py-3"><StatusBadge status={s.status} /></td>
                  <td className="px-4 py-3 text-slate-600">{s.manufacturer}</td>
                  <td className="px-4 py-3 text-slate-600">{s.model}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{s.installed_at?.substring(0, 10)}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{s.last_calibrated_at?.substring(0, 10)}</td>
                  <td className="px-4 py-3">
                    <span className={s.zone_mappings_count > 1 ? 'text-red-600 font-medium' : 'text-slate-500'}>
                      {s.zone_mappings_count}
                      {s.zone_mappings_count > 1 && ' (multi-zone!)'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {data && <p className="text-sm text-slate-500">Showing {data.length} sensors</p>}
    </div>
  )
}
