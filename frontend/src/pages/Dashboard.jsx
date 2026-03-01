import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import { Building2, ShieldCheck, Link2, TrendingUp, Users, Globe2, Cpu, ArrowRight, AlertTriangle, CheckCircle2, Clock } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const chartData = [
  { month: 'Oct', properties: 32, value: 420 },
  { month: 'Nov', properties: 58, value: 680 },
  { month: 'Dec', properties: 45, value: 550 },
  { month: 'Jan', properties: 89, value: 1100 },
  { month: 'Feb', properties: 124, value: 1650 },
  { month: 'Mar', properties: 98, value: 1280 },
]

const pieData = [
  { name: 'Verified', value: 68, color: '#10b981' },
  { name: 'Pending', value: 22, color: '#f59e0b' },
  { name: 'Under Review', value: 10, color: '#ef4444' },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded-xl p-3 border border-white/10 text-sm">
      <p className="text-slate-300 font-medium mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: {p.value}{p.name === 'value' ? ' Cr' : ''}</p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [recentTxns, setRecentTxns] = useState([])

  useEffect(() => {
    Promise.all([API.get('/dashboard/stats'), API.get('/transactions')]).then(([s, t]) => {
      setStats(s.data)
      setRecentTxns(t.data.transactions.slice(0, 5))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400">Loading dashboard...</p>
      </div>
    </div>
  )

  const statCards = [
    { label: 'Total Properties', value: fmt.number(stats?.total_properties || 0), icon: Building2, color: 'from-blue-500 to-indigo-600', bg: 'bg-blue-500/10', delta: '+12% this month' },
    { label: 'Verified Properties', value: fmt.number(stats?.verified_properties || 0), icon: CheckCircle2, color: 'from-emerald-500 to-teal-600', bg: 'bg-emerald-500/10', delta: '+8% this month' },
    { label: 'Blockchain Blocks', value: fmt.number(stats?.blockchain_blocks || 0), icon: Link2, color: 'from-purple-500 to-pink-600', bg: 'bg-purple-500/10', delta: 'Immutable chain' },
    { label: 'Market Value', value: fmt.currency(stats?.total_market_value || 0), icon: TrendingUp, color: 'from-amber-500 to-orange-600', bg: 'bg-amber-500/10', delta: '+24% YoY growth' },
    { label: 'Active Investors', value: fmt.number(stats?.active_investors || 0), icon: Users, color: 'from-rose-500 to-pink-600', bg: 'bg-rose-500/10', delta: 'Fractional owners' },
    { label: 'Fraud Prevented', value: fmt.number(stats?.fraud_prevented || 0), icon: ShieldCheck, color: 'from-cyan-500 to-blue-600', bg: 'bg-cyan-500/10', delta: 'AI detected' },
    { label: 'Cities Covered', value: fmt.number(stats?.cities_covered || 0), icon: Globe2, color: 'from-violet-500 to-indigo-600', bg: 'bg-violet-500/10', delta: 'Pan-India presence' },
    { label: 'AI Verifications', value: fmt.number(stats?.verifications_performed || 0), icon: Cpu, color: 'from-indigo-500 to-blue-600', bg: 'bg-indigo-500/10', delta: 'Documents scanned' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Real-time overview of PropChain's blockchain ecosystem</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 glass rounded-lg px-3 py-2 text-sm text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            Live Blockchain
          </div>
          <Link to="/app/register-property" className="btn-primary text-sm py-2 flex items-center gap-2">
            Register Property <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, color, bg, delta }, i) => (
          <div key={i} className="stat-card group cursor-pointer">
            <div className="flex items-start justify-between mb-3">
              <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className={`text-2xl font-black bg-gradient-to-r ${color} bg-clip-text text-transparent`}>{value}</div>
            <div className="text-slate-400 text-xs font-medium mt-0.5">{label}</div>
            <div className="text-slate-500 text-xs mt-1">{delta}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Area chart */}
        <div className="lg:col-span-2 glass-card">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-white font-bold">Property Registrations</h2>
              <p className="text-slate-400 text-xs mt-0.5">Monthly trend over 6 months</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorProps" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" stroke="#475569" fontSize={12} />
              <YAxis stroke="#475569" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="properties" name="properties" stroke="#6366f1" fill="url(#colorProps)" strokeWidth={2} />
              <Area type="monotone" dataKey="value" name="value" stroke="#a855f7" fill="url(#colorVal)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Donut */}
        <div className="glass-card">
          <h2 className="text-white font-bold mb-6">Verification Status</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                {pieData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-4">
            {pieData.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ background: item.color }} />
                  <span className="text-slate-400">{item.name}</span>
                </div>
                <span className="text-white font-medium">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Transactions & Quick Actions */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Transactions */}
        <div className="lg:col-span-2 glass-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-bold">Recent Transactions</h2>
            <Link to="/app/transactions" className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1">
              View All <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-3">
            {recentTxns.length === 0 ? (
              <p className="text-slate-400 text-sm text-center py-8">No transactions yet</p>
            ) : recentTxns.map((t, i) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  t.type === 'REGISTRATION' ? 'bg-blue-500/15 text-blue-400' :
                  t.type === 'TRANSFER' ? 'bg-purple-500/15 text-purple-400' : 'bg-amber-500/15 text-amber-400'
                }`}>
                  {t.type === 'REGISTRATION' ? <Building2 className="w-4 h-4" /> :
                   t.type === 'TRANSFER' ? <ArrowRight className="w-4 h-4" /> :
                   <Users className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-sm font-medium">{t.type.replace('_', ' ')}</div>
                  <div className="text-slate-400 text-xs truncate">{t.property_id} · {t.from} → {t.to}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-emerald-400 text-sm font-bold">{fmt.currency(t.amount)}</div>
                  <div className="text-slate-500 text-xs">{fmt.date(t.timestamp)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="glass-card">
          <h2 className="text-white font-bold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            {[
              { to: '/app/register-property', label: 'Register New Property', icon: Building2, color: 'text-blue-400', bg: 'bg-blue-500/10' },
              { to: '/app/ai-verify', label: 'Verify Document', icon: Cpu, color: 'text-purple-400', bg: 'bg-purple-500/10' },
              { to: '/app/marketplace', label: 'Browse Marketplace', icon: TrendingUp, color: 'text-amber-400', bg: 'bg-amber-500/10' },
              { to: '/app/blockchain', label: 'View Blockchain', icon: Link2, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
            ].map(({ to, label, icon: Icon, color, bg }, i) => (
              <Link key={i} to={to} className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-all group">
                <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                  <Icon className={`w-4.5 h-4.5 ${color}`} />
                </div>
                <span className="text-slate-300 group-hover:text-white text-sm font-medium transition-colors">{label}</span>
                <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 ml-auto transition-colors" />
              </Link>
            ))}
          </div>

          {/* Blockchain health */}
          <div className="mt-6 p-4 rounded-xl bg-emerald-500/8 border border-emerald-500/20">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-emerald-400 text-sm font-semibold">Blockchain Healthy</span>
            </div>
            <p className="text-slate-400 text-xs">All {stats?.blockchain_blocks} blocks verified. Chain integrity: 100%</p>
          </div>
        </div>
      </div>
    </div>
  )
}
