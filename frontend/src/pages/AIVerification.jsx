import React, { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import API from '../utils/api'
import toast from 'react-hot-toast'
import {
  Shield, Upload, CheckCircle2, XCircle, AlertTriangle, Cpu,
  FileText, Link2, Clock, ChevronDown, ChevronUp, Hash, Info,
  Building2, Zap, Eye, WifiOff
} from 'lucide-react'

const DOC_TYPES = [
  { value: 'Title Deed',               label: 'Title Deed',               icon: '📋' },
  { value: 'Sale Agreement',           label: 'Sale Agreement',           icon: '🤝' },
  { value: 'Aadhaar Card',             label: 'Aadhaar Card',             icon: '🪪' },
  { value: 'Encumbrance Certificate',  label: 'Encumbrance Certificate',  icon: '🏛️' },
  { value: 'Mutation Certificate',     label: 'Mutation Certificate',     icon: '📜' },
  { value: 'Property Tax Receipt',     label: 'Property Tax Receipt',     icon: '🧾' },
  { value: 'No Objection Certificate', label: 'NOC',                      icon: '✅' },
]

const SCORE_THRESHOLDS = {
  safe:    { color: 'text-emerald-400', bg: 'from-emerald-500 to-teal-500',  border: 'border-emerald-500/30', bgCard: 'bg-emerald-500/5' },
  caution: { color: 'text-amber-400',   bg: 'from-amber-500 to-orange-500',  border: 'border-amber-500/30',   bgCard: 'bg-amber-500/5'   },
  danger:  { color: 'text-red-400',     bg: 'from-red-500 to-rose-500',      border: 'border-red-500/30',     bgCard: 'bg-red-500/5'     },
}

function getScoreConfig(score, verdict) {
  if (verdict === 'AUTHENTIC' || score >= 85) return SCORE_THRESHOLDS.safe
  if (verdict === 'SUSPICIOUS' || score >= 60) return SCORE_THRESHOLDS.caution
  return SCORE_THRESHOLDS.danger
}

function VerifyResult({ result, onReset }) {
  const [showExtracted, setShowExtracted] = useState(false)
  const verdict      = result.verdict || result.authenticity || 'UNKNOWN'
  const score        = result.overall_score ?? Math.round((1 - (result.fraud_score || 0)) * 100)
  const cfg          = getScoreConfig(score, verdict)
  const checks       = result.checks || []
  const flags        = result.fraud_indicators || result.flags || []
  const extracted    = result.extracted_fields || []
  const blockHash    = result.block_hash || result.blockchain_block?.hash
  const isAuthentic  = result.is_authentic ?? (verdict === 'AUTHENTIC')

  return (
    <div className="space-y-4">
      {/* Header card */}
      <div className={`glass-card border ${cfg.border} ${cfg.bgCard}`}>
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-2xl ${cfg.bgCard} border ${cfg.border} flex items-center justify-center flex-shrink-0`}>
            {isAuthentic
              ? <CheckCircle2 className="w-7 h-7 text-emerald-400" />
              : verdict === 'SUSPICIOUS'
              ? <AlertTriangle className="w-7 h-7 text-amber-400" />
              : <XCircle className="w-7 h-7 text-red-400" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className={`text-2xl font-black ${cfg.color}`}>{verdict}</div>
            <div className="text-slate-400 text-xs mt-0.5">
              {result.filename || result.file_name} · {result.size_kb || result.file_size_kb} KB · {result.processing_time_ms}ms
            </div>
            <div className="text-slate-500 text-xs">{result.ml_model || result.verified_by}</div>
          </div>
          <div className="text-center flex-shrink-0">
            <div className={`text-3xl font-black ${cfg.color}`}>{score}</div>
            <div className="text-slate-500 text-xs">/ 100</div>
            <div className="text-slate-500 text-xs">Trust Score</div>
          </div>
        </div>

        {/* Score bar */}
        <div className="mt-5">
          <div className="flex justify-between text-xs text-slate-400 mb-1.5">
            <span>Trust Score</span><span>{score}/100</span>
          </div>
          <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
            <div className={`h-full bg-gradient-to-r ${cfg.bg} rounded-full transition-all duration-700`} style={{ width: `${score}%` }} />
          </div>
        </div>

        {/* Raw fraud score */}
        {result.fraud_score !== undefined && (
          <div className="mt-3 flex items-center gap-2 text-xs">
            <Info className="w-3 h-3 text-slate-500" />
            <span className="text-slate-500">Raw fraud score:</span>
            <span className={`font-bold ${result.fraud_score < 0.35 ? 'text-emerald-400' : result.fraud_score < 0.65 ? 'text-amber-400' : 'text-red-400'}`}>
              {(result.fraud_score * 100).toFixed(1)}%
            </span>
          </div>
        )}

        {/* AI explanation */}
        {result.ai_explanation && (
          <div className="mt-4 p-3 rounded-xl bg-white/3 border border-white/5">
            <div className="flex items-center gap-2 mb-1.5">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-xs font-semibold text-slate-300">Nova Pro Assessment</span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed">{result.ai_explanation}</p>
          </div>
        )}

        {/* Blockchain record */}
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

      {/* Document hash */}
      {result.document_hash && (
        <div className="glass-card py-3 flex items-center gap-3">
          <Hash className="w-4 h-4 text-slate-500 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">Document SHA-256 Hash</div>
            <div className="hash-text text-xs mt-0.5 truncate">{result.document_hash}</div>
          </div>
        </div>
      )}

      {/* Checks */}
      {checks.length > 0 && (
        <div className="glass-card">
          <h3 className="text-white font-bold mb-4 text-sm flex items-center gap-2">
            <Eye className="w-4 h-4 text-slate-400" /> Fraud Detection Checks
          </h3>
          <div className="space-y-2">
            {checks.map((c, i) => (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-xl ${c.passed ? 'hover:bg-white/3' : 'bg-red-500/5 border border-red-500/15'}`}>
                {c.passed
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
                <span className={`flex-1 text-sm ${c.passed ? 'text-slate-300' : 'text-red-300'}`}>{c.check}</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.passed ? 'bg-emerald-500' : 'bg-red-500'}`} style={{ width: `${c.confidence}%` }} />
                  </div>
                  <span className={`text-xs font-bold ${c.passed ? 'text-emerald-400' : 'text-red-400'}`}>{c.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fraud indicators */}
      {flags.length > 0 && (
        <div className="glass-card border border-red-500/20">
          <h3 className="text-red-400 font-bold mb-3 flex items-center gap-2 text-sm">
            <AlertTriangle className="w-4 h-4" /> Fraud Indicators ({flags.length})
          </h3>
          <div className="space-y-2">
            {flags.map((fi, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-red-300 bg-red-500/8 rounded-lg p-2.5">
                <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />{fi}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Extracted fields */}
      {extracted.length > 0 && (
        <div className="glass-card">
          <button onClick={() => setShowExtracted(!showExtracted)}
            className="w-full flex items-center justify-between text-sm font-bold text-white">
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" /> Extracted Fields ({extracted.length})
            </span>
            {showExtracted ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          {showExtracted && (
            <div className="mt-4 space-y-1.5">
              {extracted.map((f, i) => (
                <div key={i} className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-white/3">
                  <span className="text-slate-400 text-xs font-medium flex-1">{f.key}</span>
                  <span className="text-white text-xs">{f.value}</span>
                  <span className="text-indigo-400 text-[10px] flex-shrink-0">{Math.round(f.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <button onClick={onReset} className="btn-secondary w-full">Verify Another Document</button>
    </div>
  )
}

export default function AIVerification() {
  const [docType, setDocType]       = useState('Title Deed')
  const [propertyId, setPropertyId] = useState('')
  const [file, setFile]             = useState(null)
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState(null)
  const [history, setHistory]       = useState([])
  const [aiMode, setAiMode]         = useState(null)   // null | 'aws' | 'mock'

  useEffect(() => {
    API.get('/ai/mode').then(({ data }) => setAiMode(data.mode)).catch(() => {})
  }, [])

  const onDrop = useCallback((accepted) => {
    if (accepted.length) { setFile(accepted[0]); setResult(null) }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false, accept: { 'image/*': [], 'application/pdf': [] },
  })

  const verify = async () => {
    if (!file) return toast.error('Please select a document first')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('document_type', docType)
      fd.append('file', file)
      fd.append('property_id', propertyId.trim())
      fd.append('auto_log_on_chain', propertyId.trim() ? 'true' : 'false')
      const { data } = await API.post('/ai/verify-document', fd)
      setResult(data)
      setHistory(h => [{ ...data, _docLabel: docType, _time: new Date().toLocaleTimeString() }, ...h.slice(0, 4)])
      const v = data.verdict || data.authenticity || 'UNKNOWN'
      if (v === 'AUTHENTIC') toast.success('Document verified as Authentic!')
      else if (v === 'SUSPICIOUS') toast('Suspicious document — review required', { icon: '⚠️' })
      else toast.error('Fraudulent document detected!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">AI Document Verification</h1>
          <p className="text-slate-400 mt-1">PropChain-FraudNet v2.1 — AWS Bedrock (Amazon Nova Pro)</p>
        </div>
        {aiMode === 'aws' ? (
          <div className="flex items-center gap-2 text-xs text-emerald-300 glass rounded-lg px-3 py-2 border border-emerald-500/20">
            <Zap className="w-3.5 h-3.5" /> AWS Bedrock — Nova Pro active
          </div>
        ) : aiMode === 'mock' ? (
          <div className="flex items-center gap-2 text-xs text-amber-300 glass rounded-lg px-3 py-2 border border-amber-500/20">
            <WifiOff className="w-3.5 h-3.5" /> Mock mode — set AWS keys for real AI
          </div>
        ) : null}
      </div>

      {/* Steps */}
      <div className="grid sm:grid-cols-4 gap-3">
        {[
          { step: '01', icon: Upload,   label: 'Upload Document',    desc: 'Upload sale deed, Aadhaar, or any property doc',  color: 'text-blue-400 bg-blue-500/10'      },
          { step: '02', icon: FileText, label: 'Nova Pro Vision',    desc: 'Bedrock reads the document directly as images',   color: 'text-violet-400 bg-violet-500/10'  },
          { step: '03', icon: Cpu,      label: 'AI Fraud Analysis',  desc: 'Nova Pro extracts fields and checks for fraud',   color: 'text-purple-400 bg-purple-500/10'  },
          { step: '04', icon: Link2,    label: 'Blockchain Record',  desc: 'Result is immutably logged on-chain',             color: 'text-emerald-400 bg-emerald-500/10' },
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
          {/* Doc type */}
          <div className="glass-card">
            <h2 className="text-white font-bold mb-3 text-sm">Document Type</h2>
            <div className="space-y-1.5">
              {DOC_TYPES.map(dt => (
                <button key={dt.value} onClick={() => setDocType(dt.value)}
                  className={`w-full flex items-center gap-3 p-2.5 rounded-xl transition-all text-left ${
                    docType === dt.value ? 'bg-indigo-600/20 border border-indigo-500/30 text-white' : 'hover:bg-white/5 text-slate-400 border border-transparent'
                  }`}>
                  <span className="text-lg">{dt.icon}</span>
                  <span className="font-medium text-xs flex-1">{dt.label}</span>
                  {docType === dt.value && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                </button>
              ))}
            </div>
          </div>

          {/* Property ID */}
          <div className="glass-card">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-4 h-4 text-indigo-400" />
              <h2 className="text-white font-bold text-sm">Property ID <span className="text-slate-500 font-normal text-xs">(optional)</span></h2>
            </div>
            <input type="text" value={propertyId} onChange={e => setPropertyId(e.target.value)}
              placeholder="e.g. PROP-ALPHA001" className="input-field text-sm" />
            <p className="text-slate-500 text-[11px] mt-2 leading-relaxed">
              If provided, the result will be recorded as an immutable block on the property's blockchain ledger.
            </p>
          </div>

          {/* Dropzone */}
          <div className="glass-card">
            <h2 className="text-white font-bold mb-3 text-sm">Upload File</h2>
            <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-7 text-center cursor-pointer transition-all ${
              isDragActive ? 'border-indigo-500 bg-indigo-600/10' : file ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/3'
            }`}>
              <input {...getInputProps()} />
              {file ? (
                <div>
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-white font-semibold text-sm">{file.name}</p>
                  <p className="text-slate-400 text-xs mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                  <button onClick={e => { e.stopPropagation(); setFile(null); setResult(null) }}
                    className="mt-2 text-xs text-red-400 hover:text-red-300 transition-colors">Remove</button>
                </div>
              ) : (
                <div>
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                  <p className="text-slate-300 text-sm font-medium">Drop document here</p>
                  <p className="text-slate-500 text-xs mt-1">or click to browse · PDF, JPG, PNG (max 10 MB)</p>
                </div>
              )}
            </div>

            <button onClick={verify} disabled={loading || !file}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-40 disabled:scale-100">
              {loading ? (
                <>
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  AI Analyzing...
                </>
              ) : (
                <><Shield className="w-4 h-4" /> Verify Document</>
              )}
            </button>
          </div>

          {/* History */}
          {history.length > 0 && (
            <div className="glass-card">
              <h2 className="text-white font-bold mb-3 text-sm flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-400" /> Recent Verifications
              </h2>
              <div className="space-y-1.5">
                {history.map((h, i) => {
                  const v = h.verdict || h.authenticity || 'UNKNOWN'
                  return (
                    <div key={i} onClick={() => setResult(h)}
                      className="flex items-center gap-2 p-2 rounded-lg bg-white/3 cursor-pointer hover:bg-white/5 transition-colors">
                      {v === 'AUTHENTIC' ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        : v === 'SUSPICIOUS' ? <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                        : <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-xs font-medium truncate">{h._docLabel}</p>
                        <p className="text-slate-500 text-[10px]">{h._time}</p>
                      </div>
                      <span className={`text-[10px] font-bold flex-shrink-0 ${
                        v === 'AUTHENTIC' ? 'text-emerald-400' : v === 'SUSPICIOUS' ? 'text-amber-400' : 'text-red-400'
                      }`}>{v}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right panel — results */}
        <div className="lg:col-span-3">
          {!result && !loading && (
            <div className="glass-card h-full flex flex-col items-center justify-center text-center py-20">
              <div className="w-20 h-20 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-4">
                <Shield className="w-10 h-10 text-indigo-400" />
              </div>
              <h3 className="text-white font-bold text-lg mb-2">Ready to Verify</h3>
              <p className="text-slate-400 text-sm max-w-xs">
                Upload a document and click "Verify" to run full AI fraud analysis
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['Nova Pro Field Extraction', 'Date Validation', 'Forgery Detection', 'Name Consistency', 'Blockchain Logging'].map(f => (
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
                  <Cpu className="w-7 h-7 text-indigo-400" />
                </div>
              </div>
              <h3 className="text-white font-bold text-lg mb-2">AI Analysis in Progress</h3>
              <p className="text-slate-400 text-sm mb-6">PropChain-FraudNet v2.1 is scanning your document...</p>
              <div className="space-y-2 text-left w-72">
                {['Computing document hash...', 'Sending to Nova Pro (Bedrock)...', 'Extracting document fields...', 'Applying fraud detection rules...', 'Logging result on-chain...'].map((s, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs">
                    <div className="w-3 h-3 border border-indigo-500 border-t-transparent rounded-full animate-spin flex-shrink-0" style={{ animationDelay: `${i * 120}ms` }} />
                    <span className="text-slate-400">{s}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result && <VerifyResult result={result} onReset={() => { setResult(null); setFile(null) }} />}
        </div>
      </div>
    </div>
  )
}
