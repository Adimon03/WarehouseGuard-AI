import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Warehouses from './pages/Warehouses.jsx'
import Zones from './pages/Zones.jsx'
import Sensors from './pages/Sensors.jsx'
import Alarms from './pages/Alarms.jsx'
import Inventory from './pages/Inventory.jsx'
import Inspections from './pages/Inspections.jsx'
import Remediations from './pages/Remediations.jsx'
import Analytics from './pages/Analytics.jsx'
import Validation from './pages/Validation.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="warehouses" element={<Warehouses />} />
        <Route path="zones" element={<Zones />} />
        <Route path="sensors" element={<Sensors />} />
        <Route path="alarms" element={<Alarms />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="inspections" element={<Inspections />} />
        <Route path="remediations" element={<Remediations />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="validation" element={<Validation />} />
      </Route>
    </Routes>
  )
}
