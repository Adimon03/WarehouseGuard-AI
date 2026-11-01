import { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, RadialBarChart, RadialBar,
} from 'recharts'
import { api } from '../api/client.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

export default function Analytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getOccupancyTrend(null, 48),
      api.getDoorEventStats(),
      api.getAlarmDistribution(),
      api.getInventoryImpact(),
      api.getComplianceByZone(),
      api.getAlertMetrics(),
    ])
      .then(([occ, door, dist, imp, comp, am]) => {
        setData({ occ, door, dist, imp, comp, am })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner label="Loading analytics..." />
  if (!data) return <div className="text-slate-500">Failed to load analytics data.</div>

  const severityData = data.dist?.by_severity?.map((d, i) => ({
    name: d.severity, value: d.count, fill: COLORS[i % COLORS.length],
  })) || []

  const topZones = (data.comp || []).slice(0, 10).map((z) => ({
    name: z.zone_name, compliance: z.compliance_rate,
  }))

  const topProducts = data.imp?.top_products?.map((d) => ({
    name: d.product_name, count: d.alarm_count,
  })) || []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Analytics & Insights</h2>
        <p className="text-slate-500 mt-1">Detailed analytics across all monitored facilities</p>
      </div>

      {/* Alert Metrics */}
      {data.am && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Detection Performance vs Ground Truth</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricBox label="Precision" value={`${(data.am.precision * 100).toFixed(1)}%`} color="text-brand-600" />
            <MetricBox label="Recall" value={`${(data.am.recall * 100).toFixed(1)}%`} color="text-green-600" />
            <MetricBox label="F1 Score" value={`${(data.am.f1_score * 100).toFixed(1)}%`} color="text-purple-600" />
            <MetricBox label="True Positives" value={data.am.true_positives} color="text-slate-700" />
          </div>
          <div className="flex flex-wrap gap-4 mt-4 text-sm text-slate-500">
            <span>Ground Truth Anomalies: {data.am.total_ground_truth}</span>
            <span>Detected Alarms: {data.am.total_detected}</span>
            <span>False Positives: {data.am.false_positives}</span>
            <span>False Negatives: {data.am.false_negatives}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Occupancy Trend */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Occupancy Trend (48h)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.occ}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.substring(11, 16)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="avg" stroke="#8b5cf6" strokeWidth={2} name="Avg Occupancy" />
              <Line type="monotone" dataKey="max" stroke="#ef4444" strokeWidth={1} strokeDasharray="5 5" name="Max" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Door Events */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Door Events by Hour</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.door?.hourly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-3 text-sm text-slate-500">
            <span>Total Events: {data.door?.total_events}</span>
            <span>Prolonged: {data.door?.prolonged_events}</span>
          </div>
        </div>

        {/* Alarm by Severity */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Alarms by Severity</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={severityData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {severityData.map((d, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top Affected Products */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Top Affected Products</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={topProducts} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={120} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Compliance by Zone */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <h3 className="font-semibold text-slate-800 mb-4">Top 10 Zones by Compliance Rate</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={topZones}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={60} />
            <YAxis domain={[80, 100]} tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Bar dataKey="compliance" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function MetricBox({ label, value, color }) {
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  )
}
