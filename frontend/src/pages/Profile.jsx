import React, { useEffect, useState } from 'react'
import API, { fmt } from '../utils/api'
import { useAuth } from '../context/AuthContext'
import { User, Mail, Phone, Shield, Wallet, CheckCircle2, Clock, KeyRound } from 'lucide-react'

export default function Profile() {
  const { user: localUser } = useAuth()
  const [user, setUser] = useState(localUser)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/auth/me')
      .then(({ data }) => { setUser(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  const fields = [
    { icon: User,    label: 'Full Name',       value: user?.name },
    { icon: Mail,    label: 'Email',            value: user?.email },
    { icon: Phone,   label: 'Phone',            value: user?.phone },
    { icon: KeyRound,label: 'Aadhaar',          value: user?.aadhaar ? `XXXX-XXXX-${user.aadhaar.slice(-4)}` : '—' },
    { icon: Clock,   label: 'Member Since',     value: user?.created_at ? fmt.date(user.created_at) : '—' },
  ]

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-black text-white">My Profile</h1>
        <p className="text-slate-400 mt-1">Your PropChain account details</p>
      </div>

      {/* Avatar card */}
      <div className="glass-card flex items-center gap-5">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-3xl font-black shadow-lg shadow-indigo-500/30 flex-shrink-0">
          {user?.name?.charAt(0) || 'U'}
        </div>
        <div>
          <h2 className="text-white text-xl font-bold">{user?.name}</h2>
          <p className="text-slate-400 text-sm">{user?.email}</p>
          <div className="flex items-center gap-2 mt-2">
            {user?.kyc_verified ? (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full font-medium">
                <CheckCircle2 className="w-3 h-3" /> KYC Verified
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-full font-medium">
                <Clock className="w-3 h-3" /> KYC Pending
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Wallet */}
      <div className="glass-card flex items-center gap-4 border border-emerald-500/15">
        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
          <Wallet className="w-6 h-6 text-emerald-400" />
        </div>
        <div>
          <div className="text-slate-400 text-xs font-medium">Wallet Balance</div>
          <div className="text-2xl font-black text-emerald-400">{fmt.currency(user?.wallet_balance || 0)}</div>
        </div>
      </div>

      {/* Details */}
      <div className="glass-card space-y-1">
        <h3 className="text-white font-bold mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4 text-indigo-400" /> Account Details
        </h3>
        {fields.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center justify-between p-3 rounded-xl hover:bg-white/3 transition-colors">
            <div className="flex items-center gap-3 text-slate-400 text-sm">
              <Icon className="w-4 h-4 text-slate-500 flex-shrink-0" />
              {label}
            </div>
            <span className="text-white text-sm font-medium">{value || '—'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
