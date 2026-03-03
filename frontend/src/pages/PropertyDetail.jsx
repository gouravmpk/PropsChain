import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import API, { fmt } from '../utils/api'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import {
  Building2, MapPin, Shield, Link2, ArrowLeft, CheckCircle2, Clock,
  AlertTriangle, Users, TrendingUp, FileText, Copy, Zap, ArrowRight,
  ArrowLeftRight, Coins, X, ShoppingCart, Handshake, Calculator
} from 'lucide-react'

export default function PropertyDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [prop, setProp]   = useState(null)
  const [txns, setTxns]   = useState([])
  const [investing, setInvesting] = useState(false)
  const [fracPct, setFracPct] = useState(5)
  const [loading, setLoading] = useState(true)

  // Transfer modal
  const [showTransfer, setShowTransfer] = useState(false)
  const [transferForm, setTransferForm] = useState({ new_owner_name: '', new_owner_email: '', new_owner_aadhaar: '', transfer_amount: '' })
  const [transferring, setTransferring] = useState(false)

  // Enable fractional
  const [showFractional, setShowFractional] = useState(false)
  const [totalTokens, setTotalTokens] = useState(1000)
  const [enablingFrac, setEnablingFrac] = useState(false)

  // Buy property (non-owner full purchase)
  const [showBuy, setShowBuy] = useState(false)
  const [buyAadhaar, setBuyAadhaar] = useState('')
  const [buying, setBuying] = useState(false)

  // Deal / Negotiation modal
  const [showOffer, setShowOffer] = useState(false)
  const [offerForm, setOfferForm] = useState({
    buyer_aadhaar: '',
    negotiated_price: '',
    advance_amount: '',
    installments_total: '6',
    message: '',
    payment_mode: 'installments', // 'installments' | 'lump_sum'
  })
  const [submittingOffer, setSubmittingOffer] = useState(false)

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
        property_id: id, fraction_percent: fracPct, investor_email: user?.email || 'demo@propchain.in'
      })
      toast.success(`Invested ${fmt.currency(data.amount)} for ${data.tokens} tokens!`)
      const fresh = await API.get(`/properties/${id}`)
      setProp(fresh.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Investment failed')
    } finally { setInvesting(false) }
  }

  const transfer = async () => {
    if (!transferForm.new_owner_name || !transferForm.transfer_amount)
      return toast.error('Fill in all required fields')
    setTransferring(true)
    try {
      await API.post(`/properties/${id}/transfer`, {
        property_id: id,
        ...transferForm,
        transfer_amount: parseFloat(transferForm.transfer_amount),
      })
      toast.success('Ownership transferred successfully!')
      setShowTransfer(false)
      const fresh = await API.get(`/properties/${id}`)
      setProp(fresh.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transfer failed')
    } finally { setTransferring(false) }
  }

  const enableFractional = async () => {
    setEnablingFrac(true)
    try {
      await API.post(`/properties/${id}/enable-fractional?total_tokens=${totalTokens}`)
      toast.success(`Property tokenized into ${totalTokens} shares!`)
      setShowFractional(false)
      const fresh = await API.get(`/properties/${id}`)
      setProp(fresh.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Tokenization failed')
    } finally { setEnablingFrac(false) }
  }

  const buyProperty = async () => {
    if (!buyAadhaar.trim()) return toast.error('Enter your Aadhaar number')
    setBuying(true)
    try {
      await API.post(`/properties/${id}/transfer`, {
        property_id: id,
        new_owner_name: user.name,
        new_owner_email: user.email,
        new_owner_aadhaar: buyAadhaar.trim(),
        transfer_amount: prop.market_value,
      })
      toast.success('Property purchased successfully!')
      setShowBuy(false)
      const fresh = await API.get(`/properties/${id}`)
      setProp(fresh.data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Purchase failed')
    } finally { setBuying(false) }
  }

  const makeOffer = async () => {
    if (!offerForm.buyer_aadhaar.trim()) return toast.error('Enter your Aadhaar number')
    const negPrice = parseFloat(offerForm.negotiated_price)
    const advance  = parseFloat(offerForm.advance_amount)
    const isLumpSum = offerForm.payment_mode === 'lump_sum'
    const months   = isLumpSum ? 1 : parseInt(offerForm.installments_total)
    if (!negPrice || negPrice <= 0) return toast.error('Enter a valid negotiated price')
    if (!advance  || advance  <= 0) return toast.error('Enter a valid advance amount')
    if (advance >= negPrice)         return toast.error('Advance must be less than negotiated price')
    if (!months   || months   < 1)  return toast.error('Enter a valid number of installment months')

    setSubmittingOffer(true)
    try {
      const { data } = await API.post('/deals', {
        property_id: id,
        buyer_aadhaar: offerForm.buyer_aadhaar.trim(),
        negotiated_price: negPrice,
        advance_amount: advance,
        installments_total: months,
        message: offerForm.message || undefined,
      })
      const successMsg = isLumpSum
        ? `Offer submitted! Pay ₹${fmt.currency(advance)} advance, then clear ₹${fmt.currency(negPrice - advance)} to complete.`
        : `Offer submitted! Monthly EMI: ${fmt.currency(data.monthly_emi)}`
      toast.success(successMsg)
      setShowOffer(false)
      setOfferForm({ buyer_aadhaar: '', negotiated_price: '', advance_amount: '', installments_total: '6', message: '', payment_mode: 'installments' })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit offer')
    } finally { setSubmittingOffer(false) }
  }

  const isOwner = user?.name?.toLowerCase() === prop?.owner_name?.toLowerCase()

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
      {/* Deal / Offer Negotiation Modal */}
      {showOffer && prop && (() => {
        const negP    = parseFloat(offerForm.negotiated_price) || 0
        const adv     = parseFloat(offerForm.advance_amount)  || 0
        const isLump  = offerForm.payment_mode === 'lump_sum'
        const mths    = isLump ? 1 : (parseInt(offerForm.installments_total) || 1)
        const emi     = negP > adv && mths > 0 ? Math.round((negP - adv) / mths) : 0
        const remaining = negP > adv ? Math.round(negP - adv) : 0
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 overflow-y-auto py-6">
            <div className="glass-card w-full max-w-lg border border-violet-500/20">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-bold text-lg flex items-center gap-2">
                  <Handshake className="w-5 h-5 text-violet-400" /> Negotiate a Deal
                </h2>
                <button onClick={() => setShowOffer(false)} className="text-slate-400 hover:text-white transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Asking price context */}
              <div className="p-3 rounded-xl bg-white/3 border border-white/8 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Listed Price</span>
                  <span className="text-white font-bold">{fmt.currency(prop.market_value)}</span>
                </div>
                <div className="text-xs text-slate-500 mt-0.5">{prop.title} · {prop.city}, {prop.state}</div>
              </div>

              {/* ── Step 1: Payment Mode ── */}
              <div className="mb-4">
                <p className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wide">How do you want to pay?</p>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setOfferForm(f => ({ ...f, payment_mode: 'installments' }))}
                    className={`rounded-xl border p-3 text-left transition-all ${
                      !isLump
                        ? 'border-violet-500/60 bg-violet-500/12 ring-1 ring-violet-500/40'
                        : 'border-white/10 bg-white/3 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        !isLump ? 'border-violet-400' : 'border-slate-500'
                      }`}>
                        {!isLump && <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />}
                      </div>
                      <span className={`text-sm font-bold ${!isLump ? 'text-violet-300' : 'text-slate-400'}`}>Monthly EMIs</span>
                    </div>
                    <p className="text-xs text-slate-500 pl-5">Pay advance to book, then clear the rest in monthly installments</p>
                  </button>

                  <button
                    onClick={() => setOfferForm(f => ({ ...f, payment_mode: 'lump_sum' }))}
                    className={`rounded-xl border p-3 text-left transition-all ${
                      isLump
                        ? 'border-emerald-500/60 bg-emerald-500/10 ring-1 ring-emerald-500/40'
                        : 'border-white/10 bg-white/3 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                        isLump ? 'border-emerald-400' : 'border-slate-500'
                      }`}>
                        {isLump && <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                      </div>
                      <span className={`text-sm font-bold ${isLump ? 'text-emerald-300' : 'text-slate-400'}`}>Advance + Pay Full</span>
                    </div>
                    <p className="text-xs text-slate-500 pl-5">Pay advance to book, then pay the remaining balance in one shot</p>
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {/* Buyer identity */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Your Name</label>
                    <input value={user?.name} disabled className="input-field text-sm opacity-60 cursor-not-allowed" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Your Aadhaar *</label>
                    <input
                      value={offerForm.buyer_aadhaar}
                      onChange={e => setOfferForm(f => ({ ...f, buyer_aadhaar: e.target.value }))}
                      placeholder="XXXX-XXXX-XXXX"
                      className="input-field text-sm"
                    />
                  </div>
                </div>

                {/* Negotiation price + advance */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Your Offer Price (₹) *</label>
                    <input
                      type="number"
                      value={offerForm.negotiated_price}
                      onChange={e => setOfferForm(f => ({ ...f, negotiated_price: e.target.value }))}
                      placeholder={String(Math.round(prop.market_value * 0.9))}
                      className="input-field text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Advance / Booking Amount (₹) *</label>
                    <input
                      type="number"
                      value={offerForm.advance_amount}
                      onChange={e => setOfferForm(f => ({ ...f, advance_amount: e.target.value }))}
                      placeholder={String(Math.round(prop.market_value * 0.1))}
                      className="input-field text-sm"
                    />
                  </div>
                </div>

                {/* Installments — only shown for EMI mode */}
                {!isLump && (
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Number of Monthly Installments *</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="range" min="1" max="120" step="1"
                        value={offerForm.installments_total}
                        onChange={e => setOfferForm(f => ({ ...f, installments_total: e.target.value }))}
                        className="flex-1 accent-violet-500"
                      />
                      <span className="text-white font-bold w-14 text-center">{offerForm.installments_total} mo</span>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mt-1"><span>1 month</span><span>120 months</span></div>
                  </div>
                )}

                {/* Payment breakdown preview */}
                {negP > 0 && adv > 0 && adv < negP && (
                  <div className={`rounded-xl border p-3 ${
                    isLump ? 'bg-emerald-500/6 border-emerald-500/20' : 'bg-violet-500/6 border-violet-500/20'
                  }`}>
                    <p className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">Payment Breakdown</p>
                    {isLump ? (
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-white/5 rounded-lg p-2.5 text-center">
                          <div className="text-emerald-300 font-bold text-sm">{fmt.currency(adv)}</div>
                          <div className="text-slate-500 text-xs">Advance (book now)</div>
                        </div>
                        <div className="text-slate-500 text-xs font-bold">→ then →</div>
                        <div className="flex-1 bg-white/5 rounded-lg p-2.5 text-center">
                          <div className="text-emerald-300 font-bold text-sm">{fmt.currency(remaining)}</div>
                          <div className="text-slate-500 text-xs">Remaining (one payment)</div>
                        </div>
                      </div>
                    ) : emi > 0 ? (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-white/5 rounded-lg p-2.5 text-center">
                          <div className="text-violet-300 font-bold text-sm">{fmt.currency(adv)}</div>
                          <div className="text-slate-500 text-xs">Advance</div>
                        </div>
                        <div className="bg-white/5 rounded-lg p-2.5 text-center">
                          <div className="text-violet-300 font-bold text-sm">{fmt.currency(emi)}</div>
                          <div className="text-slate-500 text-xs">Monthly EMI</div>
                        </div>
                        <div className="bg-white/5 rounded-lg p-2.5 text-center">
                          <div className="text-violet-300 font-bold text-sm">{mths} mo</div>
                          <div className="text-slate-500 text-xs">Duration</div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Message to Seller (optional)</label>
                  <textarea
                    value={offerForm.message}
                    onChange={e => setOfferForm(f => ({ ...f, message: e.target.value }))}
                    placeholder="Hi, I'm interested in this property and would like to negotiate..."
                    rows={2}
                    className="input-field text-sm resize-none"
                  />
                </div>
              </div>

              <div className="mt-4 p-3 rounded-xl bg-indigo-500/8 border border-indigo-500/20 text-xs text-indigo-300 mb-5">
                {isLump
                  ? `📋 Once the seller accepts: pay the advance to book the property, then pay the full remaining balance of ${remaining > 0 ? fmt.currency(remaining) : '…'} in one final payment. Ownership transfers automatically.`
                  : `📋 Once the seller accepts: pay the advance, then ${offerForm.installments_total} monthly installments of ${emi > 0 ? fmt.currency(emi) : '…'}. Ownership transfers automatically when fully paid.`
                }
              </div>

              <div className="flex gap-3">
                <button onClick={() => setShowOffer(false)} className="btn-secondary flex-1">Cancel</button>
                <button
                  onClick={makeOffer}
                  disabled={submittingOffer}
                  className={`flex-1 flex items-center justify-center gap-2 text-white font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 text-sm shadow-lg ${
                    isLump
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 shadow-emerald-500/20'
                      : 'bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-400 hover:to-purple-400 shadow-violet-500/20'
                  }`}
                >
                  {submittingOffer
                    ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Submitting...</>
                    : <><Handshake className="w-4 h-4" />{isLump ? 'Submit Offer (Advance + Full)' : 'Submit Offer'}</>
                  }
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Transfer Modal */}
      {showTransfer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="glass-card w-full max-w-md border border-indigo-500/20">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-white font-bold text-lg flex items-center gap-2">
                <ArrowLeftRight className="w-5 h-5 text-indigo-400" /> Transfer Ownership
              </h2>
              <button onClick={() => setShowTransfer(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3">
              {[
                { label: 'New Owner Name *', key: 'new_owner_name', placeholder: 'Priya Sharma' },
                { label: 'New Owner Email *', key: 'new_owner_email', placeholder: 'priya@email.com' },
                { label: 'New Owner Aadhaar *', key: 'new_owner_aadhaar', placeholder: 'XXXX-XXXX-XXXX' },
                { label: 'Transfer Amount (₹) *', key: 'transfer_amount', placeholder: '5000000', type: 'number' },
              ].map(({ label, key, placeholder, type }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-slate-300 mb-1">{label}</label>
                  <input
                    type={type || 'text'}
                    value={transferForm[key]}
                    onChange={e => setTransferForm(f => ({ ...f, [key]: e.target.value }))}
                    placeholder={placeholder}
                    className="input-field text-sm"
                  />
                </div>
              ))}
            </div>
            <div className="mt-5 p-3 rounded-xl bg-amber-500/8 border border-amber-500/20 text-xs text-amber-300 mb-5">
              ⚠️ This action is irreversible. The transfer will be recorded as an immutable blockchain block.
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowTransfer(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={transfer} disabled={transferring} className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50">
                {transferring
                  ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Transferring...</>
                  : <><ArrowLeftRight className="w-4 h-4" />Confirm Transfer</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Enable Fractional Modal */}
      {showFractional && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="glass-card w-full max-w-md border border-amber-500/20">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-white font-bold text-lg flex items-center gap-2">
                <Coins className="w-5 h-5 text-amber-400" /> Tokenize Property
              </h2>
              <button onClick={() => setShowFractional(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Total Tokens: {fmt.number(totalTokens)}</label>
                <input
                  type="range" min="100" max="10000" step="100"
                  value={totalTokens}
                  onChange={e => setTotalTokens(+e.target.value)}
                  className="w-full accent-amber-500"
                />
                <div className="flex justify-between text-xs text-slate-500 mt-1"><span>100</span><span>10,000</span></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/3 rounded-xl p-3 text-center">
                  <div className="text-amber-400 font-bold">{fmt.currency(prop.market_value / totalTokens)}</div>
                  <div className="text-slate-500 text-xs">Price per Token</div>
                </div>
                <div className="bg-white/3 rounded-xl p-3 text-center">
                  <div className="text-white font-bold">{fmt.number(totalTokens)}</div>
                  <div className="text-slate-500 text-xs">Total Tokens</div>
                </div>
              </div>
            </div>
            <div className="mt-4 p-3 rounded-xl bg-indigo-500/8 border border-indigo-500/20 text-xs text-indigo-300 mb-5">
              Tokenization will be recorded on-chain. Investors can then purchase tokens from the Marketplace.
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowFractional(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={enableFractional} disabled={enablingFrac} className="w-full flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 text-sm shadow-lg shadow-amber-500/20">
                {enablingFrac
                  ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Tokenizing...</>
                  : <><Coins className="w-4 h-4" />Tokenize Property</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Buy Property Modal */}
      {showBuy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="glass-card w-full max-w-md border border-emerald-500/20">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-white font-bold text-lg flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-emerald-400" /> Buy Property
              </h2>
              <button onClick={() => setShowBuy(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Your Name</label>
                  <input value={user?.name} disabled className="input-field text-sm opacity-60 cursor-not-allowed" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Your Email</label>
                  <input value={user?.email} disabled className="input-field text-sm opacity-60 cursor-not-allowed" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Your Aadhaar *</label>
                <input
                  value={buyAadhaar}
                  onChange={e => setBuyAadhaar(e.target.value)}
                  placeholder="XXXX-XXXX-XXXX"
                  className="input-field text-sm"
                />
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/8 border border-emerald-500/20">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Purchase Price</span>
                  <span className="text-emerald-400 font-bold">{fmt.currency(prop.market_value)}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">{fmt.number(prop.area_sqft)} sq.ft · {prop.property_type}</div>
              </div>
            </div>
            <div className="mt-4 p-3 rounded-xl bg-amber-500/8 border border-amber-500/20 text-xs text-amber-300 mb-5">
              ⚠️ This will transfer full ownership to you and be recorded permanently on the blockchain.
            </div>
            <div className="flex gap-3">
              <button onClick={() => setShowBuy(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={buyProperty} disabled={buying} className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold py-2.5 rounded-xl transition-all disabled:opacity-50 text-sm shadow-lg shadow-emerald-500/20">
                {buying
                  ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Processing...</>
                  : <><ShoppingCart className="w-4 h-4" />Confirm Purchase</>}
              </button>
            </div>
          </div>
        </div>
      )}

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
            {!isOwner && (
              <div className="flex gap-2 mt-3 justify-end flex-wrap">
                <button
                  onClick={() => setShowBuy(true)}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 hover:bg-emerald-500/25 transition-all">
                  <ShoppingCart className="w-3.5 h-3.5" /> Buy Property
                </button>
                <button
                  onClick={() => setShowOffer(true)}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-violet-500/15 text-violet-300 border border-violet-500/20 hover:bg-violet-500/25 transition-all">
                  <Handshake className="w-3.5 h-3.5" /> Negotiate
                </button>
              </div>
            )}
            {isOwner && (
              <div className="flex gap-2 mt-3 justify-end">
                <button
                  onClick={() => setShowTransfer(true)}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-600/30 transition-all">
                  <ArrowLeftRight className="w-3.5 h-3.5" /> Transfer
                </button>
                {!prop.fractional_enabled && (
                  <button
                    onClick={() => setShowFractional(true)}
                    className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/20 hover:bg-amber-500/25 transition-all">
                    <Coins className="w-3.5 h-3.5" /> Tokenize
                  </button>
                )}
              </div>
            )}
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
                  <div className="hash-text" title={prop.blockchain_hash}>{fmt.shortHash(prop.blockchain_hash)}</div>
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
                  <div className="hash-text mt-1" title={t.block_hash}>{fmt.shortHash(t.block_hash)}</div>
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
            <div className="glass-card border border-emerald-500/15">
              <div className="flex items-center gap-2 mb-4">
                <ShoppingCart className="w-5 h-5 text-emerald-400" />
                <h2 className="text-white font-bold">Buy This Property</h2>
              </div>
              <div className="space-y-3 mb-4">
                <div className="bg-white/3 rounded-xl p-3 text-center">
                  <div className="text-emerald-400 font-black text-xl">{fmt.currency(prop.market_value)}</div>
                  <div className="text-slate-500 text-xs">Full Purchase Price</div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-white/3 rounded-lg p-2 text-center">
                    <div className="text-white font-bold">{fmt.number(prop.area_sqft)}</div>
                    <div className="text-slate-500">sq.ft</div>
                  </div>
                  <div className="bg-white/3 rounded-lg p-2 text-center">
                    <div className="text-white font-bold">{prop.property_type}</div>
                    <div className="text-slate-500">Type</div>
                  </div>
                </div>
              </div>
              {isOwner ? (
                <p className="text-slate-500 text-xs text-center">You own this property</p>
              ) : (
                <div className="space-y-2">
                  <button onClick={() => setShowBuy(true)}
                    className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-white font-bold py-3 rounded-xl transition-all text-sm shadow-lg shadow-emerald-500/20">
                    <ShoppingCart className="w-4 h-4" /> Buy Now
                  </button>
                  <button onClick={() => setShowOffer(true)}
                    className="w-full flex items-center justify-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-lg bg-violet-500/10 text-violet-300 border border-violet-500/20 hover:bg-violet-500/20 hover:border-violet-400/40 transition-all">
                    <Handshake className="w-3.5 h-3.5" /> Negotiate a Deal
                  </button>
                </div>
              )}
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
