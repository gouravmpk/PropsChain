import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import API from '../utils/api'
import toast from 'react-hot-toast'
import {
  GitCompare, Upload, CheckCircle2, XCircle, AlertTriangle, Cpu,
  FileText, Link2, ChevronDown, ChevronUp, Building2, Zap, X,
  ShieldCheck, ShieldAlert, ShieldX, Info
} from 'lucide-react'

const DOC_TYPES = [
  'Title Deed', 'Sale Agreement', 'Aadhaar Card', 'PAN Card',
  'Encumbrance Certificate', 'Mutation Certificate',
  'Property Tax Receipt', 'No Objection Certificate',
]

const SEVERITY_CONFIG = {
  HIGH:   { color: 'text-red-400',    bg: 'bg-red-500/10',    border: 'border-red-500/20'    },
  MEDIUM: { color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/20'  },
  LOW:    { color: 'text-blue-400',   bg: 'bg-blue-500/10',   border: 'border-blue-500/20'   },
}

const VERDICT_CONFIG = {
  CONSISTENT:   { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', Icon: ShieldCheck },
  SUSPICIOUS:   { color: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   Icon: ShieldAlert  },
  INCONSISTENT: { color: 'text-red-400',     bg: 'bg-red-500/10',     border: 'border-red-500/30',     Icon: ShieldX      },
}

function ScoreRing({ score, verdict }) {
  const cfg = VERDICT_CONFIG[verdict] || VERDICT_CONFIG.SUSPICIOUS
  const circumference = 2 * Math.PI * 36
  const offset = circumference * (1 - score / 100)
  return (
    <div className="relative w-24 h-24 flex-shrink-0">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
        <circle
          cx="40" cy="40" r="36" fill="none"
          stroke={verdict === 'CONSISTENT' ? '#10b981' : verdict === 'SUSPICIOUS' ? '#f59e0b' : '#ef4444'}
          strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-black ${cfg.color}`}>{score}</span>
        <span className="text-slate-500 text-[10px]">/ 100</span>
      </div>
    </div>
  )
}

function InconsistencyCard({ item }) {
  const [open, setOpen] = useState(false)
  const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.LOW
  return (
    <div className={`rounded-xl border ${sev.border} ${sev.bg} overflow-hidden`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 p-3 text-left"
      >
        <AlertTriangle className={`w-4 h-4 flex-shrink-0 ${sev.color}`} />
        <div className="flex-1 min-w-0">
          <span className={`font-semibold text-sm ${sev.color}`}>{item.field}</span>
          <span className="text-slate-400 text-xs ml-2">
            {item.documents_involved?.join(' vs ')}
          </span>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${sev.border} ${sev.color}`}>
          {item.severity}
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-white/5 pt-2">
          <p className="text-slate-300 text-xs leading-relaxed">{item.description}</p>
          {item.values && Object.keys(item.values).length > 0 && (
            <div className="space-y-1">
              {Object.entries(item.values).map(([doc, val]) => (
                <div key={doc} className="flex gap-2 text-xs">
                  <span className="text-slate-500 flex-shrink-0 w-32 truncate">{doc}:</span>
                  <span className="text-white font-medium">{val}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PerDocCard({ doc }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="glass-card">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between text-sm font-bold text-white"
      >
        <span className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-indigo-400" />
          {doc.document_type}
          <span className="text-slate-500 font-normal text-xs">{doc.file_name}</span>
        </span>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {open && doc.extracted?.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {doc.extracted.map((f, i) => (
            <div key={i} className="flex items-center justify-between gap-3 p-2 rounded-lg bg-white/3">
              <span className="text-slate-400 text-xs flex-1">{f.key}</span>
              <span className="text-white text-xs">{f.value}</span>
              <span className="text-indigo-400 text-[10px] flex-shrink-0">
                {Math.round((f.confidence || 0) * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CrossVerifyResult({ result, onReset }) {
  const verdict = result.overall_verdict || 'SUSPICIOUS'
  const cfg = VERDICT_CONFIG[verdict] || VERDICT_CONFIG.SUSPICIOUS
  const { Icon } = cfg
  const score = result.consistency_score ?? 50
  const inconsistencies = result.inconsistencies || []
  const perDoc = result.per_doc_results || []
  const blockHash = result.block_hash

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className={`glass-card border ${cfg.border} ${cfg.bg}`}>
        <div className="flex items-center gap-4">
          <ScoreRing score={score} verdict={verdict} />
          <div className="flex-1 min-w-0">
            <div className={`text-2xl font-black ${cfg.color}`}>{verdict}</div>
            <div className="text-slate-400 text-sm mt-0.5">
              {result.documents_analyzed} documents · {result.processing_time_ms}ms
            </div>
            <div className="text-slate-500 text-xs">{result.verified_by}</div>
          </div>
          <div className="flex-shrink-0">
            <div className={`w-14 h-14 rounded-2xl ${cfg.bg} border ${cfg.border} flex items-center justify-center`}>
              <Icon className={`w-7 h-7 ${cfg.color}`} />
            </div>
          </div>
        </div>

        {/* AI summary */}
        {result.ai_summary && (
          <div className="mt-4 p-3 rounded-xl bg-white/3 border border-white/5">
            <div className="flex items-center gap-2 mb-1.5">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-xs font-semibold text-slate-300">Nova Pro Assessment</span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed">{result.ai_summary}</p>
          </div>
        )}

        {/* On-chain */}
        {blockHash ? (
          <div className="mt-3 p-3 rounded-xl bg-white/3 flex items-center gap-2">
            <Link2 className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <span className="text-slate-400 text-xs flex-shrink-0">On-chain:</span>
            <span className="hash-text text-xs truncate">{blockHash}</span>
          </div>
        ) : (
          <div className="mt-3 p-3 rounded-xl bg-white/3 flex items-center gap-2 text-xs text-slate-500">
            <Link2 className="w-3.5 h-3.5 flex-shrink-0" />
            Not logged on-chain — provide a Property ID to enable
          </div>
        )}
      </div>

      {/* Inconsistencies */}
      {inconsistencies.length > 0 ? (
        <div className="glass-card border border-red-500/20">
          <h3 className="text-red-400 font-bold mb-3 flex items-center gap-2 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Inconsistencies Found ({inconsistencies.length})
          </h3>
          <div className="space-y-2">
            {inconsistencies.map((inc, i) => (
              <InconsistencyCard key={i} item={inc} />
            ))}
          </div>
        </div>
      ) : (
        <div className="glass-card border border-emerald-500/20 flex items-center gap-3 py-4">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <div>
            <p className="text-emerald-400 font-semibold text-sm">No Inconsistencies Detected</p>
            <p className="text-slate-400 text-xs">All cross-checked fields are consistent across documents.</p>
          </div>
        </div>
      )}

      {/* Per-doc extracted fields */}
      {perDoc.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-400" /> Extracted Fields Per Document
          </h3>
          {perDoc.map((doc, i) => <PerDocCard key={i} doc={doc} />)}
        </div>
      )}

      <button onClick={onReset} className="btn-secondary w-full">Check Another Set</button>
    </div>
  )
}

export default function CrossVerify() {
  const [files, setFiles] = useState([])     // [{file: File, docType: str}]
  const [propertyId, setPropertyId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const onDrop = useCallback((accepted) => {
    setResult(null)
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.file.name))
      const newOnes = accepted
        .filter(f => !existing.has(f.name))
        .map(f => ({ file: f, docType: 'Title Deed' }))
      const merged = [...prev, ...newOnes].slice(0, 5)
      return merged
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: { 'image/*': [], 'application/pdf': [] },
  })

  const removeFile = (idx) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
    setResult(null)
  }

  const updateDocType = (idx, docType) => {
    setFiles(prev => prev.map((f, i) => i === idx ? { ...f, docType } : f))
  }

  const verify = async () => {
    if (files.length < 2) return toast.error('Upload at least 2 documents')
    setLoading(true)
    try {
      const fd = new FormData()
      files.forEach(({ file }) => fd.append('files', file))
      fd.append('document_types', JSON.stringify(
        files.map(({ file, docType }) => ({ file_name: file.name, document_type: docType }))
      ))
      fd.append('property_id', propertyId.trim())
      fd.append('auto_log_on_chain', propertyId.trim() ? 'true' : 'false')

      const { data } = await API.post('/ai/cross-verify', fd)
      setResult(data)

      const v = data.overall_verdict
      if (v === 'CONSISTENT') toast.success('All documents are consistent!')
      else if (v === 'SUSPICIOUS') toast('Suspicious inconsistencies found — review required', { icon: '⚠️' })
      else toast.error(`${data.inconsistencies?.length || 0} inconsistencies detected!`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Cross-verification failed')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => { setFiles([]); setResult(null) }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white flex items-center gap-3">
            <GitCompare className="w-8 h-8 text-indigo-400" />
            Cross-Document Check
          </h1>
          <p className="text-slate-400 mt-1">
            Upload 2–5 documents — AI checks consistency of owner names, survey numbers, dates, and amounts across all of them
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-indigo-300 glass rounded-lg px-3 py-2 border border-indigo-500/20">
          <Zap className="w-3.5 h-3.5" /> Single Bedrock call · All docs at once
        </div>
      </div>

      {/* How it works */}
      <div className="grid sm:grid-cols-4 gap-3">
        {[
          { step: '01', icon: Upload,      label: 'Upload 2–5 Docs',         desc: 'Title deed, Aadhaar, sale agreement, tax receipt…',   color: 'text-blue-400 bg-blue-500/10'     },
          { step: '02', icon: Cpu,         label: 'Single AI Call',           desc: 'Claude reads ALL documents in one Bedrock call',       color: 'text-violet-400 bg-violet-500/10' },
          { step: '03', icon: GitCompare,  label: 'Cross-Check Fields',       desc: 'Names, survey nos., dates, amounts compared',         color: 'text-purple-400 bg-purple-500/10' },
          { step: '04', icon: ShieldCheck, label: 'Consistency Score',        desc: 'Inconsistencies flagged with HIGH/MEDIUM/LOW severity',color: 'text-emerald-400 bg-emerald-500/10' },
        ].map(({ step, icon: Icon, label, desc, color }) => (
          <div key={step} className="glass-card text-center py-4 px-3">
            <div className={`w-9 h-9 rounded-xl ${color} flex items-center justify-center mx-auto mb-2`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="text-[10px] text-slate-500 font-mono mb-1">STEP {step}</div>
            <div className="text-white font-bold text-xs mb-1">{label}</div>
            <div className="text-slate-400 text-[11px] leading-relaxed">{desc}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-5 gap-6">
        {/* Left panel */}
        <div className="lg:col-span-2 space-y-4">

          {/* Dropzone */}
          <div className="glass-card">
            <h2 className="text-white font-bold mb-3 text-sm">
              Upload Documents
              <span className="text-slate-500 font-normal ml-1 text-xs">({files.length}/5)</span>
            </h2>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all ${
                isDragActive
                  ? 'border-indigo-500 bg-indigo-600/10'
                  : files.length >= 5
                  ? 'border-white/5 opacity-40 cursor-not-allowed'
                  : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/3'
              }`}
            >
              <input {...getInputProps()} disabled={files.length >= 5} />
              <Upload className={`w-7 h-7 mx-auto mb-2 ${isDragActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              <p className="text-slate-300 text-sm font-medium">
                {files.length >= 5 ? 'Maximum 5 documents' : 'Drop documents here'}
              </p>
              <p className="text-slate-500 text-xs mt-1">PDF, JPG, PNG · max 10 MB each</p>
            </div>

            {/* File list */}
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                {files.map(({ file, docType }, idx) => (
                  <div key={idx} className="p-2.5 rounded-xl bg-white/3 border border-white/5 space-y-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      <span className="text-white text-xs font-medium flex-1 truncate">{file.name}</span>
                      <span className="text-slate-500 text-[10px] flex-shrink-0">{(file.size / 1024).toFixed(0)} KB</span>
                      <button onClick={() => removeFile(idx)} className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <select
                      value={docType}
                      onChange={e => updateDocType(idx, e.target.value)}
                      className="input-field text-xs py-1.5 w-full"
                    >
                      {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Property ID */}
          <div className="glass-card">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-indigo-400" />
              <h2 className="text-white font-bold text-sm">
                Property ID <span className="text-slate-500 font-normal text-xs">(optional)</span>
              </h2>
            </div>
            <input
              type="text"
              value={propertyId}
              onChange={e => setPropertyId(e.target.value)}
              placeholder="e.g. PROP-ALPHA001"
              className="input-field text-sm"
            />
            <p className="text-slate-500 text-[11px] mt-2 leading-relaxed">
              If provided, the cross-check result is logged as an immutable blockchain block.
            </p>
          </div>

          {/* Validation hint */}
          {files.length === 1 && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300">
              <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              Add at least one more document to enable cross-checking.
            </div>
          )}

          <button
            onClick={verify}
            disabled={loading || files.length < 2}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-40 disabled:scale-100"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI Cross-Checking…
              </>
            ) : (
              <><GitCompare className="w-4 h-4" /> Cross-Verify {files.length >= 2 ? `${files.length} Documents` : 'Documents'}</>
            )}
          </button>
        </div>

        {/* Right panel */}
        <div className="lg:col-span-3">
          {!result && !loading && (
            <div className="glass-card h-full flex flex-col items-center justify-center text-center py-20">
              <div className="w-20 h-20 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                <GitCompare className="w-10 h-10 text-indigo-400" />
              </div>
              <h3 className="text-white font-bold text-lg mb-2">Multi-Document AI Check</h3>
              <p className="text-slate-400 text-sm max-w-xs">
                Upload 2–5 property documents and let Claude find inconsistencies across all of them in one shot
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['Owner Name Match', 'Survey Number', 'Date Logic', 'Amount Consistency', 'Address Match'].map(f => (
                  <span key={f} className="text-xs text-indigo-300 bg-indigo-600/10 border border-indigo-500/20 px-2.5 py-1 rounded-full">{f}</span>
                ))}
              </div>
            </div>
          )}

          {loading && (
            <div className="glass-card h-full flex flex-col items-center justify-center text-center py-16">
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-full border-2 border-indigo-500/30" />
                <div className="absolute inset-2 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <GitCompare className="w-7 h-7 text-indigo-400" />
                </div>
              </div>
              <h3 className="text-white font-bold text-lg mb-2">Cross-Checking {files.length} Documents</h3>
              <p className="text-slate-400 text-sm mb-6">Claude is reading all documents in a single AI call…</p>
              <div className="space-y-2 text-left w-72">
                {[
                  'Converting documents to images…',
                  'Sending all docs to Bedrock in one call…',
                  'Extracting fields per document…',
                  'Cross-checking names, dates, amounts…',
                  'Computing consistency score…',
                ].map((s, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs">
                    <div className="w-3 h-3 border border-indigo-500 border-t-transparent rounded-full animate-spin flex-shrink-0" style={{ animationDelay: `${i * 120}ms` }} />
                    <span className="text-slate-400">{s}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result && <CrossVerifyResult result={result} onReset={reset} />}
        </div>
      </div>
    </div>
  )
}
