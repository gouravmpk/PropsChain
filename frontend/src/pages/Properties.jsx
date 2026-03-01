import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import { Building2, Search, Filter, MapPin, CheckCircle2, Clock, AlertTriangle, ArrowRight, TrendingUp, Eye } from 'lucide-react'

const STATUS_CONFIG = {
  Verified:      { cls: 'badge-verified', icon: CheckCircle2 },
  Pending:       { cls: 'badge-pending', icon: Clock },
  'Under Review':{ cls: 'badge-review', icon: AlertTriangle },
}

export default function Properties() {
  const [properties, setProperties] = useState([])
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')

  const load = async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (filterStatus) params.set('status', filterStatus)
    if (filterType) params.set('prop_type', filterType)
    const { data } = await API.get(`/properties?${params}`)
    setProperties(data.properties)
    setLoading(false)
  }

  useEffect(() => { load() }, [filterStatus, filterType])

  const filtered = properties.filter(p =>
    `${p.title} ${p.city} ${p.address} ${p.owner_name}`.toLowerCase().includes(search.toLowerCase())
  )

  const typeColors = {
    Commercial:  'text-blue-400 bg-blue-500/10',
    Residential: 'text-emerald-400 bg-emerald-500/10',
    Healthcare:  'text-rose-400 bg-rose-500/10',
    Industrial:  'text-orange-400 bg-orange-500/10',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Properties</h1>
          <p className="text-slate-400 mt-1">{filtered.length} properties on blockchain</p>
        </div>
        <Link to="/app/register-property" className="btn-primary text-sm flex items-center gap-2 self-start">
          <Building2 className="w-4 h-4" /> Register New
        </Link>
      </div>

      {/* Filters */}
      <div className="glass-card">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-48 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by title, city, owner..."
              className="input-field pl-10 py-2.5 text-sm" />
          </div>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            className="input-field py-2.5 text-sm w-auto min-w-36">
            <option value="">All Statuses</option>
            <option>Verified</option>
            <option>Pending</option>
            <option>Under Review</option>
          </select>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="input-field py-2.5 text-sm w-auto min-w-36">
            <option value="">All Types</option>
            <option>Commercial</option>
            <option>Residential</option>
            <option>Healthcare</option>
            <option>Industrial</option>
          </select>
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass-card shimmer h-56 rounded-2xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-card text-center py-16">
          <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No properties found</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filtered.map(p => {
            const sc = STATUS_CONFIG[p.status] || STATUS_CONFIG['Pending']
            const Icon = sc.icon
            const typeColor = typeColors[p.property_type] || 'text-slate-400 bg-slate-500/10'
            return (
              <Link key={p.id} to={`/app/properties/${p.id}`}
                className="property-card glass-card hover:border-indigo-500/30 group block">
                {/* Top */}
                <div className="flex items-start justify-between mb-3">
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-lg ${typeColor}`}>{p.property_type}</span>
                  <span className={sc.cls}><Icon className="w-3 h-3" />{p.status}</span>
                </div>

                {/* Property icon */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-600/30 to-purple-600/30 border border-indigo-500/20 flex items-center justify-center mb-3">
                  <Building2 className="w-6 h-6 text-indigo-400" />
                </div>

                <h3 className="text-white font-bold text-base mb-1 group-hover:text-indigo-300 transition-colors line-clamp-1">{p.title}</h3>
                <div className="flex items-center gap-1 text-slate-400 text-xs mb-3">
                  <MapPin className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate">{p.address}, {p.city}</span>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-white/3 rounded-lg p-2.5">
                    <div className="text-white font-bold text-sm">{fmt.currency(p.market_value)}</div>
                    <div className="text-slate-500 text-xs">Market Value</div>
                  </div>
                  <div className="bg-white/3 rounded-lg p-2.5">
                    <div className="text-white font-bold text-sm">{fmt.number(p.area_sqft)} sq.ft</div>
                    <div className="text-slate-500 text-xs">Total Area</div>
                  </div>
                </div>

                {/* Fractional badge */}
                {p.fractional_enabled && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-amber-400 font-medium flex items-center gap-1"><TrendingUp className="w-3 h-3" />Fractional</span>
                      <span className="text-slate-400">{Math.round(((p.total_tokens - p.available_tokens) / p.total_tokens) * 100)}% sold</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full"
                        style={{ width: `${((p.total_tokens - p.available_tokens) / p.total_tokens) * 100}%` }} />
                    </div>
                  </div>
                )}

                {/* Hash */}
                <div className="mt-2 pt-3 border-t border-white/5">
                  <div className="hash-text">{p.blockchain_hash?.slice(0, 36)}...</div>
                </div>

                {/* CTA */}
                <div className="mt-3 flex items-center gap-1 text-indigo-400 text-sm font-medium group-hover:gap-2 transition-all">
                  <Eye className="w-4 h-4" /> View Passport <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
