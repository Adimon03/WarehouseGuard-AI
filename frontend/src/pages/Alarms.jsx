import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Alarms() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ severity: '', status: '', alarm_type: '' })

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (filters.severity) params.set('severity', filters.severity)
    if (filters.status) params.set('status', filters.status)
    if (filters.alarm_type) params.set('alarm_type', filters.alarm_type)
    params.set('limit', 200)
    api.getAlarms('?' + params.toString())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [filters])

  async function handleAck(id) {
    await api.acknowledgeAlarm(id, 'dashboard_user')
    setFilters({ ...filters }) // trigger reload
  }
  async function handleResolve(id) {
    await api.resolveAlarm(id, 'dashboard_user')
    setFilters({ ...filters })
  }

  if (loading) return <LoadingSpinner label="Loading alarms..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Alarm Management</h2>
        <p className="text-slate-500 mt-1">Monitor and manage detected anomalies</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
        <select value={filters.alarm_type} onChange={(e) => setFilters({ ...filters, alarm_type: e.target.value })}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Types</option>
          <option value="temperature_violation">Temperature</option>
          <option value="humidity_violation">Humidity</option>
          <option value="prolonged_door_open">Door Open</option>
          <option value="abnormal_occupancy">Occupancy</option>
          <option value="sensor_outage">Sensor Outage</option>
          <option value="sensor_drift">Sensor Drift</option>
          <option value="inventory_incompatible_zone">Incompatible Zone</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Zone</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Affected Inv.</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Source</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.data?.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{a.id}</td>
                  <td className="px-4 py-3 text-slate-700">{a.alarm_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3"><StatusBadge status={a.severity} /></td>
                  <td className="px-4 py-3 text-slate-700">{a.zone_name || a.zone_id}</td>
                  <td className="px-4 py-3 text-slate-600 max-w-md truncate" title={a.description}>{a.description}</td>
                  <td className="px-4 py-3 text-slate-700">{a.affected_inventory_ids?.length || 0}</td>
                  <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded ${a.source === 'preexisting' ? 'bg-amber-50 text-amber-600' : 'bg-blue-50 text-blue-600'}`}>
                      {a.source}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {a.status === 'active' && (
                        <button onClick={() => handleAck(a.id)}
                          className="text-xs px-2 py-1 bg-amber-50 text-amber-600 rounded hover:bg-amber-100">
                          Ack
                        </button>
                      )}
                      {a.status !== 'resolved' && (
                        <button onClick={() => handleResolve(a.id)}
                          className="text-xs px-2 py-1 bg-green-50 text-green-600 rounded hover:bg-green-100">
                          Resolve
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {data && <p className="text-sm text-slate-500">Showing {data.data.length} of {data.total} alarms</p>}
    </div>
  )
}
