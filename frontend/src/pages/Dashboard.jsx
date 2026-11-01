import { useEffect, useState } from 'react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  Warehouse, Grid3x3, Cpu, Bell, AlertTriangle, ShieldCheck,
  Activity, Package, TrendingUp,
} from 'lucide-react'
import { api } from '../api/client.js'
import KpiCard from '../components/KpiCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function Dashboard() {
  const [kpis, setKpis] = useState(null)
  const [tempTrend, setTempTrend] = useState([])
  const [humTrend, setHumTrend] = useState([])
  const [alarmDist, setAlarmDist] = useState(null)
  const [sensorHealth, setSensorHealth] = useState(null)
  const [alertMetrics, setAlertMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      api.getKpis(),
      api.getTempTrend(null, 48),
      api.getHumidityTrend(null, 48),
      api.getAlarmDistribution(),
      api.getSensorHealth(),
      api.getAlertMetrics(),
    ])
      .then(([k, tt, ht, ad, sh, am]) => {
        setKpis(k)
        setTempTrend(tt)
        setHumTrend(ht)
        setAlarmDist(ad)
        setSensorHealth(sh)
        setAlertMetrics(am)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner label="Loading dashboard data..." />
  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <p className="font-medium">Error loading dashboard</p>
        <p className="text-sm mt-1">{error}</p>
        <p className="text-sm mt-2">Make sure the backend is running and data has been generated.</p>
      </div>
    )

  const alarmTypeData = alarmDist?.by_type?.map((d, i) => ({
    name: d.type.replace(/_/g, ' '),
    count: d.count,
    fill: COLORS[i % COLORS.length],
  })) || []

  const alarmSeverityData = alarmDist?.by_severity?.map((d, i) => ({
    name: d.severity,
    value: d.count,
    fill: COLORS[i % COLORS.length],
  })) || []

  const sensorStatusData = sensorHealth?.by_status?.map((d, i) => ({
    name: d.status,
    value: d.count,
    fill: COLORS[i % COLORS.length],
  })) || []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Executive Overview</h2>
        <p className="text-slate-500 mt-1">Real-time warehouse monitoring and risk metrics</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <KpiCard label="Warehouses" value={kpis.total_warehouses} icon={Warehouse} color="brand" />
        <KpiCard label="Zones" value={kpis.total_zones} icon={Grid3x3} color="slate" />
        <KpiCard label="Sensors" value={kpis.total_sensors} icon={Cpu} color="slate" />
        <KpiCard label="Sensor Readings" value={kpis.total_readings.toLocaleString()} icon={Activity} color="slate" />
        <KpiCard label="Inventory Lots" value={kpis.total_inventory_lots.toLocaleString()} icon={Package} color="purple" />
        <KpiCard label="Active Alarms" value={kpis.active_alarms} icon={Bell} color="red" />
        <KpiCard label="Critical Alarms" value={kpis.critical_alarms} icon={AlertTriangle} color="red" />
        <KpiCard label="Affected Inventory" value={kpis.affected_inventory_lots} icon={ShieldCheck} color="amber" />
      </div>

      {/* Compliance KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Env. Compliance" value={`${kpis.environmental_compliance_rate}%`} icon={ShieldCheck} color="green"
          subtext="Readings within zone limits" />
        <KpiCard label="Sensor Availability" value={`${kpis.sensor_availability}%`} icon={Activity} color="green"
          subtext={`${kpis.missing_reading_pct}% missing`} />
        <KpiCard label="Open Inspections" value={kpis.open_inspections} icon={TrendingUp} color="amber" />
        <KpiCard label="Open Remediations" value={kpis.open_remediations} icon={TrendingUp} color="amber" />
      </div>

      {/* MTTA / MTTR */}
      {kpis.mean_time_to_acknowledge_hours !== null && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <KpiCard label="Mean Time to Acknowledge" value={`${kpis.mean_time_to_acknowledge_hours}h`} icon={Activity} color="slate" />
          <KpiCard label="Mean Time to Resolve" value={kpis.mean_time_to_resolve_hours ? `${kpis.mean_time_to_resolve_hours}h` : 'N/A'} icon={Activity} color="slate" />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Trend */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Temperature Trend (48h)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={tempTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.substring(11, 16)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="max" stroke="#ef4444" fill="#fef2f2" name="Max" />
              <Area type="monotone" dataKey="avg" stroke="#3b82f6" fill="#dbeafe" name="Avg" />
              <Area type="monotone" dataKey="min" stroke="#10b981" fill="#f0fdf4" name="Min" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Humidity Trend */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Humidity Trend (48h)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={humTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} tickFormatter={(v) => v?.substring(11, 16)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="max" stroke="#ef4444" fill="#fef2f2" name="Max" />
              <Area type="monotone" dataKey="avg" stroke="#8b5cf6" fill="#ede9fe" name="Avg" />
              <Area type="monotone" dataKey="min" stroke="#10b981" fill="#f0fdf4" name="Min" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Alarm Distribution by Type */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Alarms by Type</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={alarmTypeData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Sensor Health */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Sensor Health</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={sensorStatusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {sensorStatusData.map((d, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alert Metrics */}
      {alertMetrics && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Detection Performance (vs Ground Truth)</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-brand-600">{(alertMetrics.precision * 100).toFixed(1)}%</div>
              <div className="text-xs text-slate-500 mt-1">Precision</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{(alertMetrics.recall * 100).toFixed(1)}%</div>
              <div className="text-xs text-slate-500 mt-1">Recall</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{(alertMetrics.f1_score * 100).toFixed(1)}%</div>
              <div className="text-xs text-slate-500 mt-1">F1 Score</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-slate-700">{alertMetrics.true_positives}</div>
              <div className="text-xs text-slate-500 mt-1">True Positives</div>
            </div>
          </div>
          <div className="flex justify-center gap-6 mt-4 text-sm text-slate-500">
            <span>Ground Truth: {alertMetrics.total_ground_truth}</span>
            <span>Detected: {alertMetrics.total_detected}</span>
            <span>False Positives: {alertMetrics.false_positives}</span>
            <span>False Negatives: {alertMetrics.false_negatives}</span>
          </div>
        </div>
      )}
    </div>
  )
}
