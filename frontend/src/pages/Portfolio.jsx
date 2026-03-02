import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import {
  Building2, TrendingUp, MapPin, CheckCircle2, Clock,
  AlertTriangle, ArrowRight, Wallet, Users, Eye, X, LogOut
} from 'lucide-react'

const STATUS_CONFIG = {
  Verified:      { cls: 'badge-verified', icon: CheckCircle2 },
  Pending:       { cls: 'badge-pending', icon: Clock },
  'Under Review':{ cls: 'badge-review', icon: AlertTriangle },
}

export default function Portfolio() {
  const { user } = useAuth()
  const [properties, setProperties] = useState([])
  const [holdings, setHoldings] = useState([])
  const [loading, setLoading] = useState(true)

  // Sell modal
  const [sellTarget, setSellTarget] = useState(null)   // holding object
  const [sellQty, setSellQty] = useState(1)
  const [selling, setSelling] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await API.get('/properties')
      const all = data.properties || []

      const owned = all.filter(p =>
        p.owner_name?.toLowerCase() === user?.name?.toLowerCase()
      )
      setProperties(owned)

      const fractional = all.filter(p => p.fractional_enabled)
      const holderResults = await Promise.all(
        fractional.map(p => API.get(`/properties/${p.id}`).catch(() => null))
      )
      const userHoldings = []
      holderResults.forEach((res, i) => {
        if (!res) return
        const holders = res.data.holders || []
        const match = holders.find(h => h.email === user?.email)
        if (match) userHoldings.push({ property: fractional[i], ...match })
      })
      setHoldings(userHoldings)
    } catch (err) {
      console.error('Portfolio load error:', err)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { load().catch(() => setLoading(false)) }, [load])

  const openSell = (holding) => {
    setSellTarget(holding)
    setSellQty(1)
  }

  const confirmSell = async () => {
    if (!sellTarget) return
    setSelling(true)
    try {
      const { data } = await API.post('/fractional/sell', {
        property_id: sellTarget.property.id,
        investor_email: user.email,
        tokens_to_sell: sellQty,
      })
      toast.success(`Sold ${sellQty} tokens — refund ${fmt.currency(data.refund)}`)
      setSellTarget(null)
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Sale failed')
    } finally { setSelling(false) }
  }

  const totalPropertyValue = properties.reduce((s, p) => s + (p.market_value || 0), 0)
  const totalInvested = holdings.reduce((s, h) => s + (h.invested || 0), 0)

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  const refundPreview = sellTarget ? sellQty * sellTarget.property.token_price : 0

  return (
    <div className="space-y-8">

      {/* Sell Modal */}
      {sellTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="glass-card w-full max-w-md border border-rose-500/20">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-white font-bold text-lg flex items-center gap-2">
                <LogOut className="w-5 h-5 text-rose-400" /> Sell Tokens
              </h2>
              <button onClick={() => setSellTarget(null)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-white/3 mb-4">
              <div className="text-white font-semibold text-sm">{sellTarget.property.title}</div>
              <div className="text-slate-400 text-xs mt-0.5">{sellTarget.property.city}, {sellTarget.property.state}</div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-5 text-center">
              <div className="bg-white/3 rounded-xl p-2.5">
                <div className="text-amber-400 font-bold">{sellTarget.tokens}</div>
                <div className="text-slate-500 text-xs">Your Tokens</div>
              </div>
              <div className="bg-white/3 rounded-xl p-2.5">
                <div className="text-white font-bold">{fmt.currency(sellTarget.property.token_price)}</div>
                <div className="text-slate-500 text-xs">Per Token</div>
              </div>
              <div className="bg-white/3 rounded-xl p-2.5">
                <div className="text-emerald-400 font-bold">{fmt.currency(sellTarget.invested)}</div>
                <div className="text-slate-500 text-xs">Invested</div>
              </div>
            </div>

            <div className="mb-5">
              <label className="text-sm text-slate-300 mb-2 block">
                Tokens to sell: <span className="text-white font-bold">{sellQty}</span>
                <span className="text-slate-500 ml-2">(of {sellTarget.tokens})</span>
              </label>
              <input
                type="range" min="1" max={sellTarget.tokens} step="1"
                value={sellQty}
                onChange={e => setSellQty(+e.target.value)}
                className="w-full accent-rose-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>1 token</span><span>{sellTarget.tokens} tokens (all)</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-rose-500/8 border border-rose-500/20 mb-5">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">You will receive</span>
                <span className="text-emerald-400 font-bold">{fmt.currency(refundPreview)}</span>
              </div>
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>Tokens returned to pool</span>
                <span>{sellQty} tokens</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setSellTarget(null)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={confirmSell} disabled={selling}
                className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-400 hover:to-pink-400 text-white font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 text-sm shadow-lg shadow-rose-500/20">
                {selling
                  ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Processing...</>
                  : <><LogOut className="w-4 h-4" />Confirm Sale</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white">My Portfolio</h1>
        <p className="text-slate-400 mt-1">Your owned properties and fractional token holdings</p>
      </div>

      {/* Summary cards */}
      <div className="grid sm:grid-cols-3 gap-4">
        <div className="stat-card">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center mb-3">
            <Building2 className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-2xl font-black bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            {properties.length}
          </div>
          <div className="text-slate-400 text-xs font-medium mt-0.5">Properties Owned</div>
          <div className="text-slate-500 text-xs mt-1">{fmt.currency(totalPropertyValue)} total value</div>
        </div>

        <div className="stat-card">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3">
            <TrendingUp className="w-5 h-5 text-amber-400" />
          </div>
          <div className="text-2xl font-black bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
            {holdings.length}
          </div>
          <div className="text-slate-400 text-xs font-medium mt-0.5">Fractional Investments</div>
          <div className="text-slate-500 text-xs mt-1">{fmt.currency(totalInvested)} invested</div>
        </div>

        <div className="stat-card">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3">
            <Wallet className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-2xl font-black bg-gradient-to-r from-emerald-400 to-teal-500 bg-clip-text text-transparent">
            {fmt.currency(user?.wallet_balance || 0)}
          </div>
          <div className="text-slate-400 text-xs font-medium mt-0.5">Wallet Balance</div>
          <div className="text-slate-500 text-xs mt-1">Available funds</div>
        </div>
      </div>

      {/* Owned Properties */}
      <div>
        <h2 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-indigo-400" /> Owned Properties
        </h2>
        {properties.length === 0 ? (
          <div className="glass-card text-center py-12">
            <Building2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No properties registered under your name</p>
            <Link to="/app/register-property" className="btn-primary inline-flex items-center gap-2 mt-4 text-sm px-5 py-2.5">
              Register Property <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
            {properties.map(p => {
              const sc = STATUS_CONFIG[p.status] || STATUS_CONFIG['Pending']
              const Icon = sc.icon
              return (
                <Link key={p.id} to={`/app/properties/${p.id}`}
                  className="property-card glass-card hover:border-indigo-500/30 group block">
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-xs font-medium px-2.5 py-1 rounded-lg text-indigo-300 bg-indigo-500/10">
                      {p.property_type}
                    </span>
                    <span className={sc.cls}><Icon className="w-3 h-3" />{p.status}</span>
                  </div>
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-600/30 to-purple-600/30 border border-indigo-500/20 flex items-center justify-center mb-3">
                    <Building2 className="w-6 h-6 text-indigo-400" />
                  </div>
                  <h3 className="text-white font-bold text-base mb-1 group-hover:text-indigo-300 transition-colors line-clamp-1">{p.title}</h3>
                  <div className="flex items-center gap-1 text-slate-400 text-xs mb-3">
                    <MapPin className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{p.city}, {p.state}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="bg-white/3 rounded-lg p-2.5">
                      <div className="text-white font-bold text-sm">{fmt.currency(p.market_value)}</div>
                      <div className="text-slate-500 text-xs">Market Value</div>
                    </div>
                    <div className="bg-white/3 rounded-lg p-2.5">
                      <div className="text-white font-bold text-sm">{fmt.number(p.area_sqft)} sq.ft</div>
                      <div className="text-slate-500 text-xs">Area</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-indigo-400 text-sm font-medium group-hover:gap-2 transition-all">
                    <Eye className="w-4 h-4" /> View Passport <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Fractional Holdings */}
      <div>
        <h2 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-amber-400" /> Fractional Holdings
        </h2>
        {holdings.length === 0 ? (
          <div className="glass-card text-center py-12">
            <TrendingUp className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 text-sm">No fractional investments yet</p>
            <Link to="/app/marketplace" className="btn-primary inline-flex items-center gap-2 mt-4 text-sm px-5 py-2.5">
              Browse Marketplace <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
            {holdings.map((h, i) => {
              const p = h.property
              const ownership = p.total_tokens > 0
                ? ((h.tokens / p.total_tokens) * 100).toFixed(2)
                : 0
              return (
                <div key={i} className="glass-card border border-amber-500/15 hover:border-amber-500/30 transition-all flex flex-col">
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-xs font-medium px-2.5 py-1 rounded-lg text-amber-300 bg-amber-500/10">
                      {p.property_type}
                    </span>
                    <span className="badge-verified">✅ Active</span>
                  </div>
                  <h3 className="text-white font-bold text-base mb-1 line-clamp-1">{p.title}</h3>
                  <div className="flex items-center gap-1 text-slate-400 text-xs mb-4">
                    <MapPin className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{p.city}, {p.state}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-amber-400 font-bold text-sm">{h.tokens}</div>
                      <div className="text-slate-500 text-xs">Tokens</div>
                    </div>
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-white font-bold text-sm">{ownership}%</div>
                      <div className="text-slate-500 text-xs">Ownership</div>
                    </div>
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-emerald-400 font-bold text-sm">{fmt.currency(h.invested)}</div>
                      <div className="text-slate-500 text-xs">Invested</div>
                    </div>
                  </div>
                  <div className="text-slate-500 text-xs mb-3 flex items-center gap-1">
                    <Users className="w-3 h-3" /> Purchased on {h.date}
                  </div>
                  <div className="flex gap-2 mt-auto">
                    <Link to={`/app/properties/${p.id}`}
                      className="flex-1 flex items-center justify-center gap-1.5 text-sm font-semibold text-amber-400 hover:text-amber-300 border border-amber-500/20 hover:border-amber-500/40 rounded-xl py-2.5 transition-all">
                      <Eye className="w-4 h-4" /> View
                    </Link>
                    <button onClick={() => openSell(h)}
                      className="flex-1 flex items-center justify-center gap-1.5 text-sm font-semibold text-rose-400 hover:text-rose-300 border border-rose-500/20 hover:border-rose-500/40 rounded-xl py-2.5 transition-all">
                      <LogOut className="w-4 h-4" /> Sell
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
