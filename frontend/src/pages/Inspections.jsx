import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Inspections() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: 200 })
    if (statusFilter) params.set('status', statusFilter)
    api.getInspections('?' + params.toString())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [statusFilter])

  async function handleComplete(id) {
    await api.completeInspection(id, 'Inspection completed via dashboard')
    setStatusFilter({ ...{} }) // trigger reload via state change
    setStatusFilter(statusFilter)
  }

  if (loading) return <LoadingSpinner label="Loading inspections..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Inspection Tracking</h2>
        <p className="text-slate-500 mt-1">Manage inspections for detected alarms</p>
      </div>

      <div className="flex gap-4">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="scheduled">Scheduled</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Alarm</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Severity</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Inspector</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Scheduled</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Findings</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.data?.map((i) => (
                <tr key={i.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{i.id}</td>
                  <td className="px-4 py-3 text-slate-700">{i.alarm_id}</td>
                  <td className="px-4 py-3 text-slate-600">{i.alarm_type?.replace(/_/g, ' ') || '—'}</td>
                  <td className="px-4 py-3">{i.severity ? <StatusBadge status={i.severity} /> : '—'}</td>
                  <td className="px-4 py-3 text-slate-700">{i.inspector_name}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{i.inspection_timestamp?.substring(0, 16)}</td>
                  <td className="px-4 py-3"><StatusBadge status={i.status} /></td>
                  <td className="px-4 py-3 text-slate-500 text-xs max-w-xs truncate">{i.findings || '—'}</td>
                  <td className="px-4 py-3">
                    {i.status === 'pending' || i.status === 'scheduled' ? (
                      <button onClick={() => handleComplete(i.id)}
                        className="text-xs px-2 py-1 bg-green-50 text-green-600 rounded hover:bg-green-100">
                        Complete
                      </button>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {data && <p className="text-sm text-slate-500">Showing {data.data.length} of {data.total} inspections</p>}
    </div>
  )
}
