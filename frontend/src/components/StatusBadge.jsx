export default function StatusBadge({ status }) {
  const styles = {
    // Alarm status
    active: 'bg-red-100 text-red-700',
    acknowledged: 'bg-amber-100 text-amber-700',
    resolved: 'bg-green-100 text-green-700',
    // Severity
    critical: 'bg-red-100 text-red-700',
    warning: 'bg-amber-100 text-amber-700',
    info: 'bg-blue-100 text-blue-700',
    // Sensor status
    online: 'bg-green-100 text-green-700',
    offline: 'bg-red-100 text-red-700',
    drift: 'bg-purple-100 text-purple-700',
    // Generic
    pending: 'bg-amber-100 text-amber-700',
    scheduled: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    cancelled: 'bg-slate-100 text-slate-500',
    'in_progress': 'bg-blue-100 text-blue-700',
    stored: 'bg-green-100 text-green-700',
    departed: 'bg-slate-100 text-slate-500',
    expired: 'bg-red-100 text-red-700',
  }

  const cls = styles[status?.toLowerCase()] || 'bg-slate-100 text-slate-600'

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status}
    </span>
  )
}
