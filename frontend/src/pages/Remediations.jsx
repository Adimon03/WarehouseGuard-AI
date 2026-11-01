import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Remediations() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ limit: 200 })
    if (statusFilter) params.set('status', statusFilter)
    api.getRemediations('?' + params.toString())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [statusFilter])

  async function handleComplete(id) {
    await api.completeRemediation(id)
    setStatusFilter(statusFilter) // trigger reload
  }

  if (loading) return <LoadingSpinner label="Loading remediations..." />

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Remediation Tracking</h2>
        <p className="text-slate-500 mt-1">Track remediation actions for critical alarms</p>
      </div>

      <div className="flex gap-4">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white">
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Alarm</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Action</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Performed By</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Date</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.data?.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-500">{r.id}</td>
                  <td className="px-4 py-3 text-slate-700">{r.alarm_id}</td>
                  <td className="px-4 py-3 text-slate-600">{r.action_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs truncate" title={r.description}>{r.description}</td>
                  <td className="px-4 py-3 text-slate-700">{r.performed_by}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{r.performed_at?.substring(0, 16)}</td>
                  <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-3">
                    {r.status !== 'completed' ? (
                      <button onClick={() => handleComplete(r.id)}
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
      {data && <p className="text-sm text-slate-500">Showing {data.data.length} of {data.total} remediations</p>}
    </div>
  )
}
