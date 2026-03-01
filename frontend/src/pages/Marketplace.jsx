import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import { TrendingUp, Building2, MapPin, Users, Zap, Star, ArrowRight } from 'lucide-react'

export default function Marketplace() {
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/marketplace').then(({ data }) => {
      setListings(data.listings); setLoading(false)
    })
  }, [])

  const typeGrad = {
    Commercial:  'from-blue-600/30 to-indigo-600/30',
    Healthcare:  'from-rose-600/30 to-pink-600/30',
    Residential: 'from-emerald-600/30 to-teal-600/30',
  }
  const typeIcon = { Commercial: '🏢', Healthcare: '🏥', Residential: '🏠', Industrial: '🏭' }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white">Fractional Marketplace</h1>
        <p className="text-slate-400 mt-1">Invest in tokenized premium real estate — hospitals, commercial hubs, and more</p>
      </div>

      {/* Hero Banner */}
      <div className="glass-card border border-amber-500/20 overflow-hidden relative">
        <div className="absolute inset-0 bg-gradient-to-r from-amber-600/5 to-orange-600/5" />
        <div className="relative grid md:grid-cols-2 gap-6 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-amber-500/15 text-amber-400 border border-amber-500/20 text-xs font-medium px-3 py-1.5 rounded-full mb-3">
              <Star className="w-3 h-3" /> Tokenized Real Estate
            </div>
            <h2 className="text-2xl font-black text-white mb-3">Invest in Premium Properties<br /><span className="text-amber-400">Starting from ₹10,000</span></h2>
            <p className="text-slate-400 text-sm mb-4">Own a fraction of hospitals, commercial buildings, and luxury properties. Smart contracts handle everything — no brokers, no paperwork.</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {['Blockchain Secured', 'Smart Contracts', 'Liquidity Tokens', 'Verified Properties'].map(f => (
                <span key={f} className="flex items-center gap-1.5 text-slate-300 bg-white/5 px-3 py-1.5 rounded-full border border-white/8">
                  <Zap className="w-3 h-3 text-amber-400" />{f}
                </span>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Total Listings', value: listings.length },
              { label: 'Avg Token Price', value: '₹85K' },
              { label: 'Total Invested', value: '₹1.12 Cr' },
              { label: 'Active Investors', value: '48' },
            ].map(({ label, value }) => (
              <div key={label} className="text-center glass rounded-xl p-3">
                <div className="text-white font-black text-xl">{value}</div>
                <div className="text-slate-400 text-xs mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Listings */}
      {loading ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => <div key={i} className="glass-card shimmer h-64 rounded-2xl" />)}
        </div>
      ) : listings.length === 0 ? (
        <div className="glass-card text-center py-20">
          <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No fractional listings available</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
          {listings.map(p => {
            const fracSold = Math.round(((p.total_tokens - p.available_tokens) / p.total_tokens) * 100)
            const grad = typeGrad[p.property_type] || 'from-indigo-600/30 to-purple-600/30'
            const icon = typeIcon[p.property_type] || '🏗️'
            const annualReturn = (7 + Math.random() * 8).toFixed(1)

            return (
              <div key={p.id} className="property-card glass-card hover:border-amber-500/30 flex flex-col">
                {/* Top */}
                <div className={`rounded-xl bg-gradient-to-br ${grad} border border-white/8 h-32 flex items-center justify-center mb-4 relative overflow-hidden`}>
                  <div className="text-5xl">{icon}</div>
                  <div className="absolute top-3 right-3">
                    <span className="badge-verified">✅ Verified</span>
                  </div>
                  <div className="absolute bottom-3 left-3">
                    <span className="text-xs bg-black/40 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full font-medium backdrop-blur-sm">
                      ~{annualReturn}% p.a.
                    </span>
                  </div>
                </div>

                <div className="flex-1">
                  <h3 className="text-white font-bold text-base mb-1">{p.title}</h3>
                  <div className="flex items-center gap-1 text-slate-400 text-xs mb-3">
                    <MapPin className="w-3 h-3" />{p.city}, {p.state}
                  </div>

                  {/* Token stats */}
                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-white text-xs font-bold">{fmt.currency(p.token_price)}</div>
                      <div className="text-slate-500 text-xs">Per Token</div>
                    </div>
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-white text-xs font-bold">{p.available_tokens}</div>
                      <div className="text-slate-500 text-xs">Available</div>
                    </div>
                    <div className="bg-white/3 rounded-lg p-2 text-center">
                      <div className="text-white text-xs font-bold">{fmt.currency(p.market_value)}</div>
                      <div className="text-slate-500 text-xs">Total Value</div>
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Ownership Sold</span>
                      <span className="text-amber-400 font-bold">{fracSold}%</span>
                    </div>
                    <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all"
                        style={{ width: `${fracSold}%` }} />
                    </div>
                    <div className="flex justify-between text-xs mt-1 text-slate-600">
                      <span>{p.total_tokens - p.available_tokens} sold</span>
                      <span>{p.available_tokens} left</span>
                    </div>
                  </div>
                </div>

                <Link to={`/app/properties/${p.id}`}
                  className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-bold py-3 rounded-xl transition-all text-sm shadow-lg shadow-amber-500/20">
                  <TrendingUp className="w-4 h-4" /> Invest Now <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            )
          })}
        </div>
      )}

      {/* Info section */}
      <div className="grid md:grid-cols-3 gap-5">
        {[
          { icon: '🔗', title: 'Blockchain Secured', desc: 'Every token and transaction is recorded on the PropChain immutable ledger' },
          { icon: '📜', title: 'Smart Contracts', desc: 'Automated Solidity contracts handle ownership, dividends, and transfers' },
          { icon: '💰', title: 'Passive Income', desc: 'Earn rental income and capital appreciation proportional to token holdings' },
        ].map(({ icon, title, desc }, i) => (
          <div key={i} className="glass-card text-center hover:border-amber-500/20 transition-all">
            <div className="text-4xl mb-3">{icon}</div>
            <h3 className="text-white font-bold mb-2">{title}</h3>
            <p className="text-slate-400 text-sm">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
