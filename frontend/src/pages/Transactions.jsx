import React, { useEffect, useState } from 'react'
import API, { fmt } from '../utils/api'
import { ArrowLeftRight, Building2, Users, ArrowRight, Copy, Filter } from 'lucide-react'
import toast from 'react-hot-toast'

const TYPE_CONFIG = {
  REGISTRATION:       { color: 'text-blue-400 bg-blue-500/10',   icon: Building2,     label: 'Registration' },
  TRANSFER:           { color: 'text-purple-400 bg-purple-500/10', icon: ArrowRight,   label: 'Transfer' },
  FRACTIONAL_PURCHASE:{ color: 'text-amber-400 bg-amber-500/10',  icon: Users,        label: 'Fractional Buy' },
}

export default function Transactions() {
  const [txns, setTxns] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    API.get('/transactions').then(({ data }) => {
      setTxns(data.transactions); setLoading(false)
    })
  }, [])

  const filtered = txns.filter(t => !filter || t.type === filter)

  const copy = (h) => { navigator.clipboard.writeText(h); toast.success('Hash copied!') }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Transactions</h1>
          <p className="text-slate-400 mt-1">{filtered.length} blockchain-confirmed transactions</p>
        </div>
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <select value={filter} onChange={e => setFilter(e.target.value)} className="input-field py-2 text-sm w-auto">
            <option value="">All Types</option>
            <option value="REGISTRATION">Registration</option>
            <option value="TRANSFER">Transfer</option>
            <option value="FRACTIONAL_PURCHASE">Fractional</option>
          </select>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Volume', value: fmt.currency(txns.reduce((s, t) => s + (t.amount || 0), 0)), color: 'text-emerald-400' },
          { label: 'Registrations', value: txns.filter(t => t.type === 'REGISTRATION').length, color: 'text-blue-400' },
          { label: 'Fractional Deals', value: txns.filter(t => t.type === 'FRACTIONAL_PURCHASE').length, color: 'text-amber-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass-card text-center">
            <div className={`text-2xl font-black ${color}`}>{value}</div>
            <div className="text-slate-400 text-xs mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <ArrowLeftRight className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No transactions found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left text-xs font-medium text-slate-500 px-4 py-3">TYPE</th>
                  <th className="text-left text-xs font-medium text-slate-500 px-4 py-3">PROPERTY</th>
                  <th className="text-left text-xs font-medium text-slate-500 px-4 py-3">FROM → TO</th>
                  <th className="text-right text-xs font-medium text-slate-500 px-4 py-3">AMOUNT</th>
                  <th className="text-left text-xs font-medium text-slate-500 px-4 py-3 hidden md:table-cell">BLOCK HASH</th>
                  <th className="text-left text-xs font-medium text-slate-500 px-4 py-3">DATE</th>
                  <th className="text-center text-xs font-medium text-slate-500 px-4 py-3">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/3">
                {filtered.map((t, i) => {
                  const tc = TYPE_CONFIG[t.type] || { color: 'text-slate-400 bg-slate-500/10', icon: ArrowLeftRight, label: t.type }
                  const Icon = tc.icon
                  return (
                    <tr key={i} className="hover:bg-white/3 transition-colors">
                      <td className="px-4 py-3">
                        <div className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-lg ${tc.color}`}>
                          <Icon className="w-3 h-3" />{tc.label}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-white text-xs font-mono">{t.property_id}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        <span className="text-slate-300">{t.from?.slice(0, 12)}</span>
                        <span className="text-slate-600 mx-1">→</span>
                        <span className="text-slate-300">{t.to?.slice(0, 12)}</span>
                      </td>
                      <td className="px-4 py-3 text-right text-emerald-400 text-sm font-bold">{fmt.currency(t.amount)}</td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <button onClick={() => copy(t.block_hash)}
                          className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors group">
                          <span className="hash-text text-indigo-400 group-hover:text-indigo-300">{t.block_hash?.slice(0, 14)}...</span>
                          <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{fmt.date(t.timestamp)}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="badge-verified text-xs">{t.status}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
