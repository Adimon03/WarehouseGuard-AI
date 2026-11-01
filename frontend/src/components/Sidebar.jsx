import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Warehouse, Grid3x3, Cpu, Bell,
  Package, ClipboardCheck, Wrench, BarChart3, ShieldCheck,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/warehouses', label: 'Warehouses', icon: Warehouse },
  { to: '/zones', label: 'Zones', icon: Grid3x3 },
  { to: '/sensors', label: 'Sensors', icon: Cpu },
  { to: '/alarms', label: 'Alarms', icon: Bell },
  { to: '/inventory', label: 'Inventory', icon: Package },
  { to: '/inspections', label: 'Inspections', icon: ClipboardCheck },
  { to: '/remediations', label: 'Remediations', icon: Wrench },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/validation', label: 'Validation', icon: ShieldCheck },
]

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0">
      <div className="px-6 py-5 border-b border-slate-700">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-brand-400" />
          WarehouseGuard
        </h1>
        <p className="text-xs text-slate-500 mt-1">AI Monitoring & Risk Mgmt</p>
      </div>

      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white border-r-4 border-brand-400'
                    : 'hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="px-6 py-4 border-t border-slate-700 text-xs text-slate-500">
        v1.0.0 &middot; Powered by AI
      </div>
    </aside>
  )
}
