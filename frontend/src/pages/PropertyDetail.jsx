import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import toast from 'react-hot-toast'
import {
  Building2, MapPin, Shield, Link2, ArrowLeft, CheckCircle2, Clock,
  AlertTriangle, Users, TrendingUp, FileText, Copy, Zap, ArrowRight
} from 'lucide-react'

export default function PropertyDetail() {
  const { id } = useParams()
  const [prop, setProp]   = useState(null)
  const [txns, setTxns]   = useState([])
  const [investing, setInvesting] = useState(false)
  const [fracPct, setFracPct] = useState(5)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([API.get(`/properties/${id}`), API.get(`/transactions/${id}`)]).then(([p, t]) => {
      setProp(p.data); setTxns(t.data.transactions); setLoading(false)
    })
  }, [id])

  const copyHash = (h) => { navigator.clipboard.writeText(h); toast.success('Hash copied!') }

  const invest = async () => {
    if (!prop.fractional_enabled) return toast.error('Not available for fractional investment')
    setInvesting(true)
    try {
      const { data } = await API.post('/fractional/invest', {
        property_id: id, fraction_percent: fracPct, investor_email: 'demo@propchain.in'
      })
      toast.success(`Invested ${fmt.currency(data.amount)} for ${data.tokens} tokens!`)
      const fresh = await API.get(`/properties/${id}`)
      setProp(fresh.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Investment failed')
    } finally { setInvesting(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
    </div>
  )
  if (!prop) return <div className="text-center text-slate-400 py-20">Property not found</div>

  const statusConfig = {
    Verified: { cls: 'badge-verified', icon: CheckCircle2, label: 'Verified on Blockchain' },
    Pending: { cls: 'badge-pending', icon: Clock, label: 'Pending Verification' },
    'Under Review': { cls: 'badge-review', icon: AlertTriangle, label: 'Under Review' },
  }
  const sc = statusConfig[prop.status] || statusConfig['Pending']
  const fracSold = prop.total_tokens > 0 ? Math.round(((prop.total_tokens - prop.available_tokens) / prop.total_tokens) * 100) : 0
  const investAmount = prop.token_price * Math.round((fracPct / 100) * prop.total_tokens)

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Back */}
      <Link to="/app/properties" className="inline-flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm">
        <ArrowLeft className="w-4 h-4" /> All Properties
      </Link>

      {/* Header */}
      <div className="glass-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-600/40 to-purple-600/40 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
              <Building2 className="w-7 h-7 text-indigo-400" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="text-xs bg-indigo-600/20 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-md font-medium">{prop.property_type}</span>
                <span className={sc.cls}><sc.icon className="w-3 h-3" />{sc.label}</span>
              </div>
              <h1 className="text-2xl font-black text-white">{prop.title}</h1>
              <div className="flex items-center gap-1.5 text-slate-400 text-sm mt-1">
                <MapPin className="w-3.5 h-3.5" />
                {prop.address}, {prop.city}, {prop.state} — {prop.pincode}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-black text-white">{fmt.currency(prop.market_value)}</div>
            <div className="text-slate-400 text-sm">{fmt.number(prop.area_sqft)} sq.ft</div>
          </div>
        </div>

        {/* AI Fraud Score */}
        <div className="mt-5 p-4 rounded-xl bg-white/3 border border-white/5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Shield className={`w-4 h-4 ${prop.fraud_score < 10 ? 'text-emerald-400' : 'text-red-400'}`} />
              <span className="text-white">AI Fraud Score</span>
            </div>
            <span className={`text-sm font-bold ${prop.fraud_score < 10 ? 'text-emerald-400' : 'text-red-400'}`}>
              {prop.fraud_score}/100 — {prop.fraud_score < 10 ? 'Low Risk' : 'Medium Risk'}
            </span>
          </div>
          <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all ${prop.fraud_score < 10 ? 'bg-gradient-to-r from-emerald-500 to-teal-500' : 'bg-gradient-to-r from-amber-500 to-orange-500'}`}
              style={{ width: `${prop.fraud_score}%` }} />
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Property Info */}
          <div className="glass-card">
            <h2 className="text-white font-bold mb-4 flex items-center gap-2"><FileText className="w-4 h-4 text-indigo-400" />Property Details</h2>
            <dl className="grid grid-cols-2 gap-4">
              {[
                { label: 'Property ID', value: prop.id },
                { label: 'Survey Number', value: prop.survey_number },
                { label: 'Owner Name', value: prop.owner_name },
                { label: 'Aadhaar (masked)', value: prop.owner_aadhaar },
                { label: 'Registered', value: fmt.date(prop.registered_at) },
                { label: 'Documents', value: prop.documents_verified ? '✅ Verified' : '⏳ Pending' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <dt className="text-slate-500 text-xs font-medium mb-0.5">{label}</dt>
                  <dd className="text-white text-sm font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            {prop.description && (
              <div className="mt-4 pt-4 border-t border-white/5">
                <dt className="text-slate-500 text-xs font-medium mb-1">Description</dt>
                <dd className="text-slate-300 text-sm leading-relaxed">{prop.description}</dd>
              </div>
            )}
          </div>

          {/* Blockchain Passport */}
          <div className="glass-card border border-indigo-500/15">
            <h2 className="text-white font-bold mb-4 flex items-center gap-2">
              <Link2 className="w-4 h-4 text-indigo-400" />Blockchain Property Passport
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-indigo-600/8 border border-indigo-500/15">
                <div>
                  <div className="text-slate-400 text-xs mb-0.5">Block Hash</div>
                  <div className="hash-text">{prop.blockchain_hash}</div>
                </div>
                <button onClick={() => copyHash(prop.blockchain_hash)}
                  className="ml-3 flex-shrink-0 text-slate-400 hover:text-white transition-colors p-1">
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                {[
                  { label: 'Block Type', value: 'PROPERTY' },
                  { label: 'Algorithm', value: 'SHA-256' },
                  { label: 'Network', value: 'PropChain' },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-white/3 rounded-xl p-3">
                    <div className="text-white text-sm font-bold">{value}</div>
                    <div className="text-slate-500 text-xs">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Transaction History */}
          <div className="glass-card">
            <h2 className="text-white font-bold mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />Transaction History
            </h2>
            {txns.length === 0 ? (
              <p className="text-slate-400 text-sm text-center py-6">No transactions yet</p>
            ) : (
              <div className="space-y-3">
                {txns.map((t, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl hover:bg-white/3 transition-colors">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{t.type.replace('_', ' ')}</span>
                        <span className="text-emerald-400 text-sm font-bold">{fmt.currency(t.amount)}</span>
                      </div>
                      <div className="text-slate-400 text-xs mt-0.5">{t.from} → {t.to}</div>
                      <div className="hash-text mt-1">{t.block_hash?.slice(0, 40)}...</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Fractional + Holders */}
        <div className="space-y-6">
          {/* Fractional Investment */}
          {prop.fractional_enabled ? (
            <div className="glass-card border border-amber-500/15">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-amber-400" />
                <h2 className="text-white font-bold">Fractional Investment</h2>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-white/3 rounded-xl p-3 text-center">
                  <div className="text-amber-400 font-bold">{fmt.currency(prop.token_price)}</div>
                  <div className="text-slate-500 text-xs">Per Token</div>
                </div>
                <div className="bg-white/3 rounded-xl p-3 text-center">
                  <div className="text-white font-bold">{prop.available_tokens}</div>
                  <div className="text-slate-500 text-xs">Available</div>
                </div>
              </div>

              <div className="mb-4">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Ownership Sold</span>
                  <span className="text-amber-400 font-medium">{fracSold}%</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full" style={{ width: `${fracSold}%` }} />
                </div>
              </div>

              <div className="mb-4">
                <label className="text-sm text-slate-300 mb-2 block">Investment Fraction: {fracPct}%</label>
                <input type="range" min="1" max="20" value={fracPct} onChange={e => setFracPct(+e.target.value)}
                  className="w-full accent-amber-500" />
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>1%</span><span>20%</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-amber-500/8 border border-amber-500/20 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Estimated Cost</span>
                  <span className="text-amber-400 font-bold">{fmt.currency(investAmount)}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>Tokens</span>
                  <span>{Math.round((fracPct / 100) * prop.total_tokens)}</span>
                </div>
              </div>

              <button onClick={invest} disabled={investing}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-bold py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20">
                {investing ? <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  : <TrendingUp className="w-4 h-4" />}
                {investing ? 'Processing...' : 'Invest Now'}
              </button>
            </div>
          ) : (
            <div className="glass-card text-center py-8">
              <TrendingUp className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">Fractional investment not available</p>
            </div>
          )}

          {/* Holders */}
          {prop.holders?.length > 0 && (
            <div className="glass-card">
              <h2 className="text-white font-bold mb-4 flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" />Token Holders ({prop.holders.length})
              </h2>
              <div className="space-y-2">
                {prop.holders.map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-2.5 rounded-xl hover:bg-white/3 transition-colors">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                        {h.investor?.charAt(0)}
                      </div>
                      <div>
                        <div className="text-white text-xs font-medium">{h.investor}</div>
                        <div className="text-slate-500 text-xs">{h.date}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-amber-400 text-xs font-bold">{h.tokens} tkns</div>
                      <div className="text-slate-500 text-xs">{fmt.currency(h.invested)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
