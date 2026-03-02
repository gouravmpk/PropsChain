import React, { useEffect, useState } from 'react'
import API, { fmt } from '../utils/api'
import toast from 'react-hot-toast'
import { Link2, CheckCircle2, Copy, RefreshCw, Shield, Cpu, Clock, Search, X } from 'lucide-react'

export default function Blockchain() {
  const [chain, setChain] = useState([])
  const [integrity, setIntegrity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hashQuery, setHashQuery] = useState('')
  const [hashResult, setHashResult] = useState(null)
  const [hashSearching, setHashSearching] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [b, v] = await Promise.all([API.get('/blockchain'), API.get('/blockchain/verify')])
      setChain([...b.data.chain].reverse())
      setIntegrity(v.data)
    } catch (err) {
      console.error('Blockchain load error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const copyHash = (h) => { navigator.clipboard.writeText(h); toast.success('Hash copied!') }

  const searchByHash = async () => {
    if (!hashQuery.trim()) return toast.error('Enter a block hash')
    setHashSearching(true)
    setHashResult(null)
    try {
      const { data } = await API.get(`/blockchain/block/${hashQuery.trim()}`)
      setHashResult(data)
    } catch {
      toast.error('Block not found')
    } finally { setHashSearching(false) }
  }

  const typeColors = {
    PROPERTY_REGISTRATION: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    PROPERTY_TRANSFER:     'text-purple-400 bg-purple-500/10 border-purple-500/20',
    FRACTIONAL_ENABLED:    'text-amber-400 bg-amber-500/10 border-amber-500/20',
    FRACTIONAL_PURCHASE:   'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    DOCUMENT_VERIFICATION: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Blockchain Ledger</h1>
          <p className="text-slate-400 mt-1">Immutable SHA-256 blockchain — every property transaction recorded forever</p>
        </div>
        <button onClick={load} className="btn-secondary text-sm flex items-center gap-2 self-start">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Hash search */}
      <div className="glass-card">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              value={hashQuery}
              onChange={e => { setHashQuery(e.target.value); setHashResult(null) }}
              onKeyDown={e => e.key === 'Enter' && searchByHash()}
              placeholder="Search by block hash (SHA-256)…"
              className="input-field pl-10 text-sm py-2.5"
            />
          </div>
          {hashQuery && (
            <button onClick={() => { setHashQuery(''); setHashResult(null) }}
              className="px-3 text-slate-400 hover:text-white transition-colors">
              <X className="w-4 h-4" />
            </button>
          )}
          <button onClick={searchByHash} disabled={hashSearching}
            className="btn-primary text-sm px-5 flex items-center gap-2 disabled:opacity-50">
            {hashSearching
              ? <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              : <Search className="w-4 h-4" />}
            Search
          </button>
        </div>

        {hashResult && (
          <div className="mt-4 p-4 rounded-xl bg-indigo-600/8 border border-indigo-500/20 space-y-3">
            <div className="flex items-center gap-2 text-sm font-bold text-white">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Block #{hashResult.block_index} found
              <span className="text-xs font-normal text-slate-400 ml-1">· {hashResult.property_id} · {hashResult.transaction_type}</span>
            </div>
            <div className="grid sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-white/3">
                <div className="text-slate-500 mb-1">Block Hash</div>
                <div className="hash-text truncate" title={hashResult.hash}>{fmt.shortHash(hashResult.hash)}</div>
              </div>
              <div className="p-2.5 rounded-lg bg-white/3">
                <div className="text-slate-500 mb-1">Previous Hash</div>
                <div className="hash-text truncate" title={hashResult.previous_hash}>{fmt.shortHash(hashResult.previous_hash)}</div>
              </div>
            </div>
            <div className="text-xs text-slate-500 flex items-center gap-1">
              <Clock className="w-3 h-3" /> {fmt.date(hashResult.timestamp)}
            </div>
          </div>
        )}
      </div>

      {/* Status */}
      {integrity && (
        <div className="grid sm:grid-cols-3 gap-4">
          <div className={`glass-card flex items-center gap-4 border ${integrity.valid ? 'border-emerald-500/20' : 'border-red-500/20'}`}>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${integrity.valid ? 'bg-emerald-500/15' : 'bg-red-500/15'}`}>
              <Shield className={`w-6 h-6 ${integrity.valid ? 'text-emerald-400' : 'text-red-400'}`} />
            </div>
            <div>
              <div className={`font-bold ${integrity.valid ? 'text-emerald-400' : 'text-red-400'}`}>
                {integrity.valid ? 'Chain Verified ✅' : 'Chain Compromised ⚠️'}
              </div>
              <div className="text-slate-500 text-xs">Integrity Status</div>
            </div>
          </div>

          <div className="glass-card flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/15 flex items-center justify-center">
              <Link2 className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <div className="text-white font-bold text-xl">{integrity.chain_length}</div>
              <div className="text-slate-500 text-xs">Total Blocks</div>
            </div>
          </div>

          <div className="glass-card flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-500/15 flex items-center justify-center">
              <Cpu className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <div className="text-white font-bold">SHA-256</div>
              <div className="text-slate-500 text-xs">Hashing Algorithm</div>
            </div>
          </div>
        </div>
      )}

      {/* Blockchain visualization */}
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : chain.map((block, i) => (
          <div key={block.index} className={`glass-card transition-all hover:border-indigo-500/30 ${block.index === 0 ? 'border border-amber-500/20' : ''}`}>
            {/* Block header */}
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className={`px-3 py-1.5 rounded-lg text-sm font-black ${block.index === 0 ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' : 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/20'}`}>
                #{block.index}
              </div>

              {block.data?.type && (
                <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${typeColors[block.data.type] || 'text-slate-400 bg-slate-500/10 border-slate-500/20'}`}>
                  {block.data.type?.replace(/_/g, ' ')}
                </span>
              )}

              <div className="flex items-center gap-1.5 text-slate-500 text-xs ml-auto">
                <Clock className="w-3 h-3" />
                {fmt.date(block.timestamp)}
              </div>

              <div className="flex items-center gap-1.5 text-emerald-400 text-xs">
                <CheckCircle2 className="w-3.5 h-3.5" /> Verified
              </div>
            </div>

            {/* Hashes */}
            <div className="grid sm:grid-cols-2 gap-3 mb-4">
              <div className="p-3 rounded-xl bg-white/3">
                <div className="text-slate-500 text-xs font-medium mb-1">Block Hash</div>
                <div className="flex items-center gap-2">
                  <div className="hash-text flex-1 truncate" title={block.hash}>{fmt.shortHash(block.hash)}</div>
                  <button onClick={() => copyHash(block.hash)} className="text-slate-500 hover:text-white flex-shrink-0 transition-colors">
                    <Copy className="w-3 h-3" />
                  </button>
                </div>
              </div>
              <div className="p-3 rounded-xl bg-white/3">
                <div className="text-slate-500 text-xs font-medium mb-1">Previous Hash</div>
                <div className="hash-text truncate" title={block.previous_hash}>{fmt.shortHash(block.previous_hash)}</div>
              </div>
            </div>

            {/* Block data */}
            {block.data && typeof block.data === 'object' && Object.keys(block.data).length > 0 && (
              <div className="p-3 rounded-xl bg-indigo-600/5 border border-indigo-500/10">
                <div className="text-slate-500 text-xs font-medium mb-2">Block Data</div>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(block.data).filter(([k]) => k !== 'type').map(([k, v]) => (
                    <div key={k} className="text-xs">
                      <span className="text-slate-500">{k}: </span>
                      <span className="text-slate-300 font-medium">{String(v).length > 20 ? String(v).slice(0,20)+'...' : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Nonce */}
            <div className="mt-3 flex items-center gap-6 text-xs text-slate-600">
              <span>Nonce: <span className="text-slate-400 font-mono">{block.nonce}</span></span>
            </div>

            {/* Connector line */}
            {i < chain.length - 1 && (
              <div className="mt-4 flex justify-center">
                <div className="w-0.5 h-4 bg-gradient-to-b from-indigo-500/50 to-transparent" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
