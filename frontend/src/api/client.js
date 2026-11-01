const BASE = '/api'

async function fetchJSON(url, options) {
  const res = await fetch(`${BASE}${url}`, options)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API error ${res.status}: ${detail}`)
  }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('json') ? res.json() : res.text()
}

export const api = {
  // System
  getStatus: () => fetchJSON('/system/status'),
  generate: (full = true) =>
    fetchJSON('/system/generate?full=' + full, { method: 'POST' }),
  detect: () => fetchJSON('/system/detect', { method: 'POST' }),
  generateAndDetect: (full = true) =>
    fetchJSON('/system/generate-and-detect?full=' + full, { method: 'POST' }),
  getDataDictionary: () => fetchJSON('/system/data-dictionary'),
  getReproducibility: () => fetchJSON('/system/reproducibility'),

  // Entities
  getWarehouses: (params = '') => fetchJSON('/warehouses/' + params),
  getZones: (params = '') => fetchJSON('/zones/' + params),
  getSensors: (params = '') => fetchJSON('/sensors/' + params),
  getReadings: (params = '') => fetchJSON('/readings/' + params),
  getDoorEvents: (params = '') => fetchJSON('/door-events/' + params),
  getInventory: (params = '') => fetchJSON('/inventory/' + params),
  getStorageRequirements: () => fetchJSON('/storage-requirements/'),
  getAlarms: (params = '') => fetchJSON('/alarms/' + params),
  getAlarm: (id) => fetchJSON(`/alarms/${id}`),
  acknowledgeAlarm: (id, by = 'system') =>
    fetchJSON(`/alarms/${id}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: by }),
    }),
  resolveAlarm: (id, by = 'system') =>
    fetchJSON(`/alarms/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolved_by: by }),
    }),
  getInspections: (params = '') => fetchJSON('/inspections/' + params),
  completeInspection: (id, findings = '') =>
    fetchJSON(`/inspections/${id}/complete?findings=${encodeURIComponent(findings)}`, { method: 'POST' }),
  getRemediations: (params = '') => fetchJSON('/remediations/' + params),
  completeRemediation: (id) =>
    fetchJSON(`/remediations/${id}/complete`, { method: 'POST' }),

  // Analytics
  getKpis: () => fetchJSON('/analytics/kpis'),
  getTempTrend: (zoneId, hours = 48) =>
    fetchJSON(`/analytics/trends/temperature?hours=${hours}${zoneId ? `&zone_id=${zoneId}` : ''}`),
  getHumidityTrend: (zoneId, hours = 48) =>
    fetchJSON(`/analytics/trends/humidity?hours=${hours}${zoneId ? `&zone_id=${zoneId}` : ''}`),
  getOccupancyTrend: (zoneId, hours = 48) =>
    fetchJSON(`/analytics/trends/occupancy?hours=${hours}${zoneId ? `&zone_id=${zoneId}` : ''}`),
  getDoorEventStats: (zoneId) =>
    fetchJSON(`/analytics/door-event-stats${zoneId ? `?zone_id=${zoneId}` : ''}`),
  getAlertMetrics: () => fetchJSON('/analytics/alert-metrics'),
  getAlarmDistribution: () => fetchJSON('/analytics/alarm-distribution'),
  getSensorHealth: () => fetchJSON('/analytics/sensor-health'),
  getInventoryImpact: () => fetchJSON('/analytics/inventory-impact'),
  getComplianceByZone: () => fetchJSON('/analytics/compliance-by-zone'),

  // Validation
  getValidationReport: () => fetchJSON('/validation/report'),

  // Exports
  exportCsv: (table) => `${BASE}/exports/csv/${table}`,
  exportJson: (table) => fetchJSON(`/exports/json/${table}`),
  getExportList: () => fetchJSON('/exports/list'),
}
