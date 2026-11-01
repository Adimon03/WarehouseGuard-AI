import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from 'lucide-react'
import { api } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function Validation() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getValidationReport()
      .then(setReport)
      .catch(() => setReport(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner label="Running validation checks..." />
  if (!report) return <div className="text-slate-500">Failed to load validation report.</div>

  const passedChecks = report.checks.filter((c) => c.status === 'pass')
  const failedChecks = report.checks.filter((c) => c.status === 'fail')
  const warningChecks = report.checks.filter((c) => c.status === 'warning')

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Data Quality & Validation</h2>
        <p className="text-slate-500 mt-1">Automated validation for data integrity and negative scenarios</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label="Total Checks" value={report.total_checks} icon={ShieldCheck} color="slate" />
        <SummaryCard label="Passed" value={report.passed} icon={CheckCircle2} color="green" />
        <SummaryCard label="Failed" value={report.failed} icon={XCircle} color="red" />
        <SummaryCard label="Warnings" value={report.warnings} icon={AlertTriangle} color="amber" />
      </div>

      {/* Failed checks */}
      {failedChecks.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-red-200 p-5">
          <h3 className="font-semibold text-red-700 mb-4 flex items-center gap-2">
            <XCircle className="w-5 h-5" /> Failed Checks ({failedChecks.length})
          </h3>
          <div className="space-y-3">
            {failedChecks.map((c, i) => (
              <div key={i} className="border border-red-100 rounded-lg p-3 bg-red-50">
                <div className="font-medium text-red-800 text-sm">{c.check}</div>
                <div className="text-xs text-red-600 mt-1">{c.detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warning checks */}
      {warningChecks.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-amber-200 p-5">
          <h3 className="font-semibold text-amber-700 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" /> Warnings ({warningChecks.length})
          </h3>
          <div className="space-y-3">
            {warningChecks.map((c, i) => (
              <div key={i} className="border border-amber-100 rounded-lg p-3 bg-amber-50">
                <div className="font-medium text-amber-800 text-sm">{c.check}</div>
                <div className="text-xs text-amber-600 mt-1">{c.detail}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Passed checks */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <h3 className="font-semibold text-green-700 mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5" /> Passed Checks ({passedChecks.length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {passedChecks.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-slate-600">
              <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
              <span>{c.check}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Negative scenarios explanation */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="font-semibold text-blue-800 mb-3">About the Negative Scenarios</h3>
        <p className="text-sm text-blue-700 mb-3">
          The following four negative scenarios are intentionally injected into the dataset to test
          that the system correctly detects them:
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex gap-2"><span className="font-medium">1.</span> Inventory lot assigned to an incompatible zone — detected by anomaly detection and validation.</div>
          <div className="flex gap-2"><span className="font-medium">2.</span> Sensor mapped to multiple zones without justification — detected by validation.</div>
          <div className="flex gap-2"><span className="font-medium">3.</span> Missing sensor readings incorrectly treated as normal — detection generates sensor_outage alarms.</div>
          <div className="flex gap-2"><span className="font-medium">4.</span> Alarm not linked to affected inventory lots — detected by validation.</div>
        </div>
        <p className="text-xs text-blue-500 mt-3">
          Failed checks for negative scenarios are expected — they confirm the system found the injected anomalies.
        </p>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, icon: Icon, color }) {
  const colors = {
    green: 'border-green-200 bg-green-50 text-green-700',
    red: 'border-red-200 bg-red-50 text-red-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
  }
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{label}</span>
        <Icon className="w-5 h-5" />
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  )
}
