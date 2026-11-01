import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Zones() {
  const [data, setData] = useState(null)
  const [compliance, setCompliance] = useState([])
  const [loading, setLoading] = useState(true)
  const [whFilter, setWhFilter] = useState('')

  useEffect(() => {
    Promise.all([
      api.getZones('?limit=500' + (whFilter ? `&warehouse_id=${whFilter}` : '')),
      api.getComplianceByZone(),
    ])
      .then(([z, c]) => { setData(z); setCompliance(c) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [whFilter])

  if (loading) return <LoadingSpinner label="Loading zones..." />

  const compMap = Object.fromEntries(compliance.map((c) => [c.zone_id, c]))

  const typeColors = {
    ambient: 'bg-blue-50 text-blue-700',
    cold_storage: 'bg-cyan-50 text-cyan-700',
    frozen: 'bg-indigo-50 text-indigo-700',
    hazardous: 'bg-red-50 text-red-700',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Zone Monitoring</h2>
          <p className="text-slate-500 mt-1">Environmental compliance across all zones</p>
        </div>
        <select value={whFilter} onChange={(e) => setWhFilter(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Warehouses</option>
          <option value="1">Warehouse 1</option>
          <option value="2">Warehouse 2</option>
          <option value="3">Warehouse 3</option>
          <option value="4">Warehouse 4</option>
          <option value="5">Warehouse 5</option>
          <option value="6">Warehouse 6</option>
          <option value="7">Warehouse 7</option>
          <option value="8">Warehouse 8</option>
          <option value="9">Warehouse 9</option>
          <option value="10">Warehouse 10</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Temp Range</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Humidity Range</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Sensors</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Inventory</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Compliance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((z) => {
                const comp = compMap[z.id]
                const rate = comp?.compliance_rate ?? 100
                const barColor = rate >= 95 ? 'bg-green-500' : rate >= 80 ? 'bg-amber-500' : 'bg-red-500'
                return (
                  <tr key={z.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-500">{z.id}</td>
                    <td className="px-4 py-3 font-medium text-slate-800">{z.name}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${typeColors[z.zone_type] || 'bg-slate-100'}`}>
                        {z.zone_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{z.min_temp_c}–{z.max_temp_c}°C</td>
                    <td className="px-4 py-3 text-slate-600">{z.min_humidity_pct}–{z.max_humidity_pct}%</td>
                    <td className="px-4 py-3 text-slate-700">{z.sensor_count}</td>
                    <td className="px-4 py-3 text-slate-700">{z.inventory_count}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div className={`h-full ${barColor}`} style={{ width: `${rate}%` }} />
                        </div>
                        <span className="text-xs text-slate-600">{rate}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
