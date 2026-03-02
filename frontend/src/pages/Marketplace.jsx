import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import { TrendingUp, Building2, MapPin, Zap, Star, ArrowRight, ShoppingCart, Home } from 'lucide-react'

const typeGrad = {
  Commercial:  'from-blue-600/30 to-indigo-600/30',
  Healthcare:  'from-rose-600/30 to-pink-600/30',
  Residential: 'from-emerald-600/30 to-teal-600/30',
  Industrial:  'from-orange-600/30 to-amber-600/30',
  Agricultural:'from-lime-600/30 to-green-600/30',
}
const typeIcon = { Commercial: '🏢', Healthcare: '🏥', Residential: '🏠', Industrial: '🏭', Agricultural: '🌾' }
const typeColors = {
  Commercial:  'text-blue-400 bg-blue-500/10',
  Residential: 'text-emerald-400 bg-emerald-500/10',
  Healthcare:  'text-rose-400 bg-rose-500/10',
  Industrial:  'text-orange-400 bg-orange-500/10',
  Agricultural:'text-green-400 bg-green-500/10 border-green-500/20',
}

export default function Marketplace() {
  const [tab, setTab] = useState('fractional')
  const [fractional, setFractional] = useState([])
  const [forSale, setForSale] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      API.get('/marketplace'),
      API.get('/properties?status=Verified'),
    ]).then(([mkt, props]) => {
      setFractional(mkt.data.listings || [])
      setForSale(props.data.properties?.filter(p => !p.fractional_enabled) || [])
      setLoading(false)
    }).catch(err => {
      console.error('Marketplace load error:', err)
      setLoading(false)
    })
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white">Marketplace</h1>
        <p className="text-slate-400 mt-1">Buy properties outright or invest in fractional tokens</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 glass-card rounded-xl w-fit">
        <button
          onClick={() => setTab('fractional')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${tab === 'fractional' ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/20' : 'text-slate-400 hover:text-white'}`}>
          <TrendingUp className="w-4 h-4" /> Fractional Investing
        </button>
        <button
          onClick={() => setTab('buy')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${tab === 'buy' ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/20' : 'text-slate-400 hover:text-white'}`}>
          <ShoppingCart className="w-4 h-4" /> Buy Property
        </button>
      </div>

      {/* ── FRACTIONAL TAB ── */}
      {tab === 'fractional' && (
        <>
          {/* Banner */}
          <div className="glass-card border border-amber-500/20 overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-amber-600/5 to-orange-600/5" />
            <div className="relative grid md:grid-cols-2 gap-6 items-center">
              <div>
                <div className="inline-flex items-center gap-2 bg-amber-500/15 text-amber-400 border border-amber-500/20 text-xs font-medium px-3 py-1.5 rounded-full mb-3">
                  <Star className="w-3 h-3" /> Tokenized Real Estate
                </div>
                <h2 className="text-2xl font-black text-white mb-3">Invest in Premium Properties<br /><span className="text-amber-400">Starting from ₹10,000</span></h2>
                <p className="text-slate-400 text-sm mb-4">Own a fraction of hospitals, commercial buildings, and luxury properties. Blockchain-secured, no brokers, no paperwork.</p>
                <div className="flex flex-wrap gap-3 text-sm">
                  {['Blockchain Secured', 'SHA-256 Verified', 'Liquidity Tokens', 'AI Verified'].map(f => (
                    <span key={f} className="flex items-center gap-1.5 text-slate-300 bg-white/5 px-3 py-1.5 rounded-full border border-white/8">
                      <Zap className="w-3 h-3 text-amber-400" />{f}
                    </span>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Fractional Listings', value: fractional.length },
                  { label: 'Min. Investment', value: '₹10K' },
                  { label: 'Properties for Sale', value: forSale.length },
                  { label: 'Blockchain Verified', value: '100%' },
                ].map(({ label, value }) => (
                  <div key={label} className="text-center glass rounded-xl p-3">
                    <div className="text-white font-black text-xl">{value}</div>
                    <div className="text-slate-400 text-xs mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
              {[...Array(3)].map((_, i) => <div key={i} className="glass-card shimmer h-64 rounded-2xl" />)}
            </div>
          ) : fractional.length === 0 ? (
            <div className="glass-card text-center py-20">
              <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No fractional listings yet</p>
              <p className="text-slate-600 text-sm mt-1">Property owners can tokenize their properties to enable fractional investing</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-6">
              {fractional.map(p => {
                const fracSold = Math.round(((p.total_tokens - p.available_tokens) / p.total_tokens) * 100)
                const grad = typeGrad[p.property_type] || 'from-indigo-600/30 to-purple-600/30'
                const icon = typeIcon[p.property_type] || '🏗️'
                return (
                  <div key={p.id} className="property-card glass-card hover:border-amber-500/30 flex flex-col">
                    <div className={`rounded-xl bg-gradient-to-br ${grad} border border-white/8 h-32 flex items-center justify-center mb-4 relative overflow-hidden`}>
                      <div className="text-5xl">{icon}</div>
                      <div className="absolute top-3 right-3">
                        <span className="badge-verified">✅ Verified</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-white font-bold text-base mb-1">{p.title}</h3>
                      <div className="flex items-center gap-1 text-slate-400 text-xs mb-3">
                        <MapPin className="w-3 h-3" />{p.city}, {p.state}
                      </div>
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
                      <div className="mb-4">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-400">Ownership Sold</span>
                          <span className="text-amber-400 font-bold">{fracSold}%</span>
                        </div>
                        <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all" style={{ width: `${fracSold}%` }} />
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
        </>
      )}

      {/* ── BUY PROPERTY TAB ── */}
      {tab === 'buy' && (
        <>
          {/* Banner */}
          <div className="glass-card border border-emerald-500/20 overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-600/5 to-teal-600/5" />
            <div className="relative flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 flex items-center justify-center flex-shrink-0">
                <Home className="w-7 h-7 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-xl font-black text-white mb-1">Buy Verified Properties Directly</h2>
                <p className="text-slate-400 text-sm">Apartments, houses, farmland, shops — blockchain-verified ownership, no middlemen. Purchase transfers instantly on-chain.</p>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
              {[...Array(4)].map((_, i) => <div key={i} className="glass-card shimmer h-52 rounded-2xl" />)}
            </div>
          ) : forSale.length === 0 ? (
            <div className="glass-card text-center py-20">
              <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No verified properties for direct sale yet</p>
              <p className="text-slate-600 text-sm mt-1">Properties appear here once they're verified on the blockchain</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
              {forSale.map(p => {
                const grad = typeGrad[p.property_type] || 'from-indigo-600/30 to-purple-600/30'
                const icon = typeIcon[p.property_type] || '🏗️'
                const typeColor = typeColors[p.property_type] || 'text-slate-400 bg-slate-500/10'
                return (
                  <div key={p.id} className="property-card glass-card hover:border-emerald-500/30 flex flex-col">
                    <div className={`rounded-xl bg-gradient-to-br ${grad} border border-white/8 h-28 flex items-center justify-center mb-4 relative overflow-hidden`}>
                      <div className="text-5xl">{icon}</div>
                      <div className="absolute top-3 right-3">
                        <span className="badge-verified">✅ Verified</span>
                      </div>
                      <div className="absolute top-3 left-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-md ${typeColor}`}>{p.property_type}</span>
                      </div>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-white font-bold text-base mb-1 line-clamp-1">{p.title}</h3>
                      <div className="flex items-center gap-1 text-slate-400 text-xs mb-3">
                        <MapPin className="w-3 h-3 flex-shrink-0" />{p.address}, {p.city}, {p.state}
                      </div>
                      <div className="grid grid-cols-2 gap-2 mb-4">
                        <div className="bg-white/3 rounded-lg p-2.5">
                          <div className="text-emerald-400 font-black text-sm">{fmt.currency(p.market_value)}</div>
                          <div className="text-slate-500 text-xs">Asking Price</div>
                        </div>
                        <div className="bg-white/3 rounded-lg p-2.5">
                          <div className="text-white font-bold text-sm">{fmt.number(p.area_sqft)} sq.ft</div>
                          <div className="text-slate-500 text-xs">Area</div>
                        </div>
                      </div>
                      <div className="hash-text mb-3" title={p.blockchain_hash}>{fmt.shortHash(p.blockchain_hash)}</div>
                    </div>
                    <Link to={`/app/properties/${p.id}`}
                      className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold py-3 rounded-xl transition-all text-sm shadow-lg shadow-emerald-500/20">
                      <ShoppingCart className="w-4 h-4" /> Buy Now <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {/* Info */}
      <div className="grid md:grid-cols-3 gap-5">
        {[
          { icon: '🔗', title: 'Blockchain Secured', desc: 'Every transaction is recorded on the PropChain immutable ledger — tamper-proof and permanent' },
          { icon: '🤖', title: 'AI Document Verified', desc: 'AWS Bedrock Nova Pro scans and verifies property documents for fraud before listing' },
          { icon: '💰', title: 'No Middlemen', desc: 'Buy or invest directly — no brokers, no paperwork, instant on-chain ownership transfer' },
        ].map(({ icon, title, desc }, i) => (
          <div key={i} className="glass-card text-center hover:border-indigo-500/20 transition-all">
            <div className="text-4xl mb-3">{icon}</div>
            <h3 className="text-white font-bold mb-2">{title}</h3>
            <p className="text-slate-400 text-sm">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
