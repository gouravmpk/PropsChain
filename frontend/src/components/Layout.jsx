import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  LayoutDashboard, Building2, PlusCircle, ShoppingBag,
  ShieldCheck, Link2, ArrowLeftRight, LogOut, Menu, X,
  ChevronRight, Wallet, Bell, User, Boxes
} from 'lucide-react'
import { fmt } from '../utils/api'

const navItems = [
  { to: '/app/dashboard',          label: 'Dashboard',       icon: LayoutDashboard },
  { to: '/app/properties',         label: 'Properties',      icon: Building2 },
  { to: '/app/register-property',  label: 'Register Property', icon: PlusCircle },
  { to: '/app/marketplace',        label: 'Marketplace',     icon: ShoppingBag },
  { to: '/app/ai-verify',          label: 'AI Verification', icon: ShieldCheck },
  { to: '/app/blockchain',         label: 'Blockchain',      icon: Link2 },
  { to: '/app/transactions',       label: 'Transactions',    icon: ArrowLeftRight },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/') }

  return (
    <div className="flex h-screen bg-[#0a0a14] overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-20 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`fixed lg:static inset-y-0 left-0 z-30 w-72 flex flex-col transform transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
        style={{ background: 'rgba(10,10,20,0.98)', borderRight: '1px solid rgba(99,102,241,0.15)' }}>

        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Boxes className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-bold text-white text-lg leading-none">PropChain</div>
              <div className="text-xs text-indigo-400 font-medium">by OpsAI</div>
            </div>
          </div>
          <button className="lg:hidden text-slate-400 hover:text-white" onClick={() => setSidebarOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User card */}
        <div className="mx-4 mt-4 p-4 rounded-xl" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-semibold text-sm truncate">{user?.name}</div>
              <div className="text-slate-400 text-xs truncate">{user?.email}</div>
            </div>
            {user?.kyc_verified && (
              <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-3 h-3 text-white" />
              </div>
            )}
          </div>
          {user?.wallet_balance && (
            <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-2">
              <Wallet className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-xs text-slate-400">Wallet:</span>
              <span className="text-xs text-emerald-400 font-semibold">{fmt.currency(user.wallet_balance)}</span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              onClick={() => setSidebarOpen(false)}>
              <Icon className="w-4.5 h-4.5 flex-shrink-0" />
              <span className="flex-1">{label}</span>
              <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100" />
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-white/5">
          <button onClick={handleLogout}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-xl text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all duration-200 font-medium">
            <LogOut className="w-4.5 h-4.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0" style={{ background: 'rgba(10,10,20,0.9)' }}>
          <div className="flex items-center gap-4">
            <button className="lg:hidden text-slate-400 hover:text-white" onClick={() => setSidebarOpen(true)}>
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <div className="text-xs text-slate-500 font-medium">Blockchain & AI Property Platform</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="w-9 h-9 rounded-lg glass flex items-center justify-center text-slate-400 hover:text-white transition-colors relative">
              <Bell className="w-4.5 h-4.5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full"></span>
            </button>
            <button className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
              {user?.name?.charAt(0) || 'U'}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
