import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import API, { fmt } from '../utils/api'
import toast from 'react-hot-toast'
import { Building2, MapPin, User, FileText, CheckCircle2, ArrowRight, Cpu, Shield, Upload, AlertTriangle, XCircle } from 'lucide-react'

const STEPS = ['Property Info', 'Location', 'Owner Details', 'Verify Doc', 'Review & Submit']

const PROPERTY_TYPES = ['Residential', 'Commercial', 'Industrial', 'Healthcare', 'Agricultural', 'Other']

function InputField({ label, fieldKey, type = 'text', placeholder, options, form, set }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
      {options ? (
        <select value={form[fieldKey]} onChange={e => set(fieldKey, e.target.value)} className="input-field">
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type} value={form[fieldKey]} onChange={e => set(fieldKey, e.target.value)}
          placeholder={placeholder} className="input-field" />
      )}
    </div>
  )
}

export default function RegisterProperty() {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [registered, setRegistered] = useState(null)
  const navigate = useNavigate()

  const [form, setForm] = useState({
    title: '', description: '', property_type: 'Residential', area_sqft: '',
    market_value: '', survey_number: '', address: '', city: '', state: '', pincode: '',
    owner_name: '', owner_aadhaar: '',
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const fieldProps = { form, set }

  // ── Document verification ─────────────────────────────────────────────────
  const [docFile, setDocFile]       = useState(null)
  const [docType, setDocType]       = useState('Title Deed')
  const [docResult, setDocResult]   = useState(null)
  const [docLoading, setDocLoading] = useState(false)

  const onDrop = useCallback((accepted) => {
    if (accepted.length) { setDocFile(accepted[0]); setDocResult(null) }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false,
    accept: { 'image/*': [], 'application/pdf': [] },
  })

  const verifyDoc = async () => {
    if (!docFile) return toast.error('Please upload a document first')
    setDocLoading(true)
    try {
      const fd = new FormData()
      fd.append('document_type', docType)
      fd.append('file', docFile)
      fd.append('property_id', '')
      fd.append('auto_log_on_chain', 'false')
      const { data } = await API.post('/ai/verify-document', fd)
      setDocResult(data)
      const v = data.verdict || data.authenticity
      if (v === 'AUTHENTIC') toast.success('Document verified as Authentic!')
      else if (v === 'SUSPICIOUS') toast('Suspicious document — you may still proceed', { icon: '⚠️' })
      else toast.error('Fraudulent document detected — cannot proceed')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed')
    } finally { setDocLoading(false) }
  }

  const docVerdict = docResult ? (docResult.verdict || docResult.authenticity) : null
  const docScore   = docResult ? (docResult.overall_score ?? Math.round((1 - (docResult.fraud_score || 0)) * 100)) : null
  const canProceed = docVerdict === 'AUTHENTIC' || docVerdict === 'SUSPICIOUS'

  const submit = async () => {
    setLoading(true)
    try {
      const payload = { ...form, area_sqft: parseFloat(form.area_sqft), market_value: parseFloat(form.market_value) }
      const { data } = await API.post('/properties/register', payload)
      setRegistered(data)
      toast.success('Property registered on blockchain!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally { setLoading(false) }
  }

  if (registered) {
    const prop = registered.property
    const block = registered.block
    return (
      <div className="max-w-2xl mx-auto">
        <div className="glass-card text-center border border-emerald-500/20">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center mx-auto mb-6 shadow-xl shadow-emerald-500/30">
            <CheckCircle2 className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-3xl font-black text-white mb-2">Property Registered!</h2>
          <p className="text-slate-400 mb-8">Your property has been added to the PropChain blockchain</p>

          <div className="space-y-3 text-left mb-8">
            {[
              { label: 'Property ID', value: prop.id, mono: true },
              { label: 'Status', value: prop.status, badge: true },
              { label: 'Fraud Score', value: `${prop.fraud_score}/100 — ${prop.fraud_score < 10 ? '✅ Low Risk' : '⚠️ Medium Risk'}` },
              { label: 'Block Hash', value: block.hash, mono: true },
              { label: 'Block Index', value: `#${block.index}` },
              { label: 'Blockchain', value: `PropChain (SHA-256)` },
            ].map(({ label, value, mono, badge }) => (
              <div key={label} className="flex items-center justify-between p-3 rounded-xl bg-white/3">
                <span className="text-slate-400 text-sm">{label}</span>
                {badge ? (
                  <span className={prop.status === 'Verified' ? 'badge-verified' : 'badge-pending'}>{value}</span>
                ) : (
                  <span className={`text-white text-sm font-medium ${mono ? 'font-mono text-xs text-indigo-300 max-w-40 truncate' : ''}`}>{value}</span>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <button onClick={() => navigate(`/app/properties/${prop.id}`)}
              className="btn-primary flex-1 flex items-center justify-center gap-2">
              View Passport <ArrowRight className="w-4 h-4" />
            </button>
            <button onClick={() => { setRegistered(null); setForm({ title:'',description:'',property_type:'Residential',area_sqft:'',market_value:'',survey_number:'',address:'',city:'',state:'',pincode:'',owner_name:'',owner_aadhaar:'' }); setDocFile(null); setDocResult(null); setDocType('Title Deed'); setStep(0) }}
              className="btn-secondary flex-1">Register Another</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white">Register Property</h1>
        <p className="text-slate-400 mt-1">Create an immutable Property Passport on PropChain blockchain</p>
      </div>

      {/* Stepper */}
      <div className="glass-card">
        <div className="flex items-center">
          {STEPS.map((s, i) => (
            <React.Fragment key={i}>
              <button onClick={() => i < step && setStep(i)}
                className={`flex items-center gap-2 transition-all ${i <= step ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  i < step ? 'bg-emerald-500 text-white' :
                  i === step ? 'bg-indigo-600 text-white ring-4 ring-indigo-500/20' :
                  'bg-white/5 text-slate-500'}`}>
                  {i < step ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
                </div>
                <span className={`hidden sm:block text-xs font-medium ${i === step ? 'text-white' : i < step ? 'text-emerald-400' : 'text-slate-500'}`}>{s}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-3 rounded-full transition-all ${i < step ? 'bg-emerald-500' : 'bg-white/5'}`} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Form steps */}
      <div className="glass-card">
        {step === 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-6">
              <Building2 className="w-5 h-5 text-indigo-400" />
              <h2 className="text-white font-bold">Property Information</h2>
            </div>
            <InputField label="Property Title *" fieldKey="title" placeholder="e.g. Premium Commercial Complex" {...fieldProps} />
            <div className="grid grid-cols-2 gap-4">
              <InputField label="Property Type *" fieldKey="property_type" options={PROPERTY_TYPES} {...fieldProps} />
              <InputField label="Survey Number *" fieldKey="survey_number" placeholder="SRV/MH/2024/0012" {...fieldProps} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <InputField label="Area (sq.ft) *" fieldKey="area_sqft" type="number" placeholder="1200" {...fieldProps} />
              <InputField label="Market Value (₹) *" fieldKey="market_value" type="number" placeholder="5000000" {...fieldProps} />
            </div>
            {form.market_value && <div className="text-indigo-400 text-sm">= {fmt.currency(parseFloat(form.market_value) || 0)}</div>}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Description</label>
              <textarea value={form.description} onChange={e => set('description', e.target.value)}
                rows={3} placeholder="Describe the property..."
                className="input-field resize-none" />
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-6">
              <MapPin className="w-5 h-5 text-indigo-400" />
              <h2 className="text-white font-bold">Location Details</h2>
            </div>
            <InputField label="Full Address *" fieldKey="address" placeholder="Plot 15, Sector 4" {...fieldProps} />
            <div className="grid grid-cols-2 gap-4">
              <InputField label="City *" fieldKey="city" placeholder="Mumbai" {...fieldProps} />
              <InputField label="State *" fieldKey="state" placeholder="Maharashtra" {...fieldProps} />
            </div>
            <InputField label="PIN Code *" fieldKey="pincode" placeholder="400001" {...fieldProps} />
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-6">
              <User className="w-5 h-5 text-indigo-400" />
              <h2 className="text-white font-bold">Owner Details</h2>
            </div>
            <InputField label="Owner Full Name *" fieldKey="owner_name" placeholder="Arjun Sharma" {...fieldProps} />
            <InputField label="Aadhaar Number *" fieldKey="owner_aadhaar" placeholder="XXXX-XXXX-XXXX" {...fieldProps} />
            <div className="p-4 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-sm text-indigo-300">
              <Cpu className="w-4 h-4 inline mr-2" />
              AI will automatically verify Aadhaar authenticity during registration
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-5 h-5 text-indigo-400" />
              <h2 className="text-white font-bold">Document Verification</h2>
            </div>
            <p className="text-slate-400 text-sm">Upload a supporting document to verify authenticity before registration.</p>

            {/* Doc type */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Document Type</label>
              <select value={docType} onChange={e => { setDocType(e.target.value); setDocResult(null) }} className="input-field">
                {['Title Deed','Sale Agreement','Encumbrance Certificate','Mutation Certificate','Property Tax Receipt','No Objection Certificate'].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Dropzone */}
            <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragActive ? 'border-indigo-500 bg-indigo-600/10' :
              docFile ? 'border-emerald-500/50 bg-emerald-500/5' :
              'border-white/10 hover:border-indigo-500/50 hover:bg-white/3'
            }`}>
              <input {...getInputProps()} />
              {docFile ? (
                <div>
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-white font-semibold text-sm">{docFile.name}</p>
                  <p className="text-slate-400 text-xs mt-1">{(docFile.size / 1024).toFixed(1)} KB</p>
                  <button onClick={e => { e.stopPropagation(); setDocFile(null); setDocResult(null) }}
                    className="mt-2 text-xs text-red-400 hover:text-red-300 transition-colors">Remove</button>
                </div>
              ) : (
                <div>
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                  <p className="text-slate-300 text-sm font-medium">Drop document here</p>
                  <p className="text-slate-500 text-xs mt-1">PDF, JPG, PNG — max 10 MB</p>
                </div>
              )}
            </div>

            <button onClick={verifyDoc} disabled={docLoading || !docFile}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-40 disabled:scale-100">
              {docLoading
                ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>AI Verifying...</>
                : <><Shield className="w-4 h-4" />Verify Document</>}
            </button>

            {/* Result panel */}
            {docResult && (
              <div className={`rounded-xl border p-4 space-y-3 ${
                docVerdict === 'AUTHENTIC' ? 'bg-emerald-500/8 border-emerald-500/25' :
                docVerdict === 'SUSPICIOUS' ? 'bg-amber-500/8 border-amber-500/25' :
                'bg-red-500/8 border-red-500/25'
              }`}>
                <div className="flex items-center gap-3">
                  {docVerdict === 'AUTHENTIC'
                    ? <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    : docVerdict === 'SUSPICIOUS'
                    ? <AlertTriangle className="w-6 h-6 text-amber-400" />
                    : <XCircle className="w-6 h-6 text-red-400" />}
                  <div>
                    <div className={`font-black text-lg ${
                      docVerdict === 'AUTHENTIC' ? 'text-emerald-400' :
                      docVerdict === 'SUSPICIOUS' ? 'text-amber-400' : 'text-red-400'
                    }`}>{docVerdict}</div>
                    <div className="text-slate-400 text-xs">Trust Score: {docScore}/100</div>
                  </div>
                </div>

                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-700 ${
                    docVerdict === 'AUTHENTIC' ? 'bg-gradient-to-r from-emerald-500 to-teal-500' :
                    docVerdict === 'SUSPICIOUS' ? 'bg-gradient-to-r from-amber-500 to-orange-500' :
                    'bg-gradient-to-r from-red-500 to-rose-500'
                  }`} style={{ width: `${docScore}%` }} />
                </div>

                {docResult.ai_explanation && (
                  <p className="text-slate-400 text-xs leading-relaxed">
                    <span className="text-slate-300 font-medium">AI: </span>{docResult.ai_explanation}
                  </p>
                )}

                {(docResult.fraud_indicators || docResult.flags || []).length > 0 && (
                  <div className="space-y-1">
                    {(docResult.fraud_indicators || docResult.flags).map((fi, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-xs text-red-300">
                        <XCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />{fi}
                      </div>
                    ))}
                  </div>
                )}

                {docVerdict === 'FRAUDULENT' && (
                  <p className="text-xs text-red-300 font-semibold">⛔ Fraudulent documents cannot be used for registration.</p>
                )}
                {docVerdict === 'SUSPICIOUS' && (
                  <p className="text-xs text-amber-300">⚠️ Suspicious document. Registration will be flagged for manual review.</p>
                )}
              </div>
            )}

            {!docResult && (
              <p className="text-slate-500 text-xs text-center">Verification required before proceeding to review.</p>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-6">
              <FileText className="w-5 h-5 text-indigo-400" />
              <h2 className="text-white font-bold">Review & Submit</h2>
            </div>
            <div className="space-y-2">
              {[
                { label: 'Title', value: form.title },
                { label: 'Type', value: form.property_type },
                { label: 'Survey No.', value: form.survey_number },
                { label: 'Area', value: `${fmt.number(parseFloat(form.area_sqft))} sq.ft` },
                { label: 'Market Value', value: fmt.currency(parseFloat(form.market_value)) },
                { label: 'Address', value: `${form.address}, ${form.city}, ${form.state}` },
                { label: 'Owner', value: form.owner_name },
                { label: 'Aadhaar', value: form.owner_aadhaar },
              ].map(({ label, value }) => value && (
                <div key={label} className="flex items-center justify-between p-3 rounded-xl bg-white/3">
                  <span className="text-slate-400 text-sm">{label}</span>
                  <span className="text-white text-sm font-medium">{value}</span>
                </div>
              ))}
            </div>
            {/* Doc verification badge */}
            {docResult && (
              <div className={`flex items-center gap-3 p-3 rounded-xl border ${
                docVerdict === 'AUTHENTIC' ? 'bg-emerald-500/8 border-emerald-500/20' : 'bg-amber-500/8 border-amber-500/20'
              }`}>
                {docVerdict === 'AUTHENTIC'
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  : <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />}
                <div className="text-sm">
                  <span className={docVerdict === 'AUTHENTIC' ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>Document {docVerdict}</span>
                  <span className="text-slate-500 text-xs ml-2">{docFile?.name} · {docScore}/100</span>
                </div>
              </div>
            )}

            <div className="p-4 rounded-xl bg-emerald-500/8 border border-emerald-500/20 text-sm text-emerald-300">
              ✅ Submitting will create an immutable blockchain record. This action cannot be undone.
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-3 mt-8">
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)} className="btn-secondary flex-1">Back</button>
          )}
          {step < 4 ? (
            <button
              onClick={() => setStep(s => s + 1)}
              disabled={step === 3 && !canProceed}
              title={step === 3 && !canProceed ? 'Verify your document before proceeding' : ''}
              className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-40 disabled:scale-100">
              {step === 3 && !canProceed
                ? 'Verify Document First'
                : <><span>Continue</span><ArrowRight className="w-4 h-4" /></>}
            </button>
          ) : (
            <button onClick={submit} disabled={loading}
              className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50">
              {loading ? <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                : <Building2 className="w-4 h-4" />}
              {loading ? 'Registering on Blockchain...' : 'Register Property'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
