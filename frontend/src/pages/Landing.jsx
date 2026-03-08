import React, { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Shield, Zap, Users, ArrowRight, ChevronRight, Check, Globe2, Lock, Cpu, Star, Building, Award } from 'lucide-react'

const FEATURES = [
  { icon: Shield, title: 'Immutable Property Passport', desc: 'Every property gets a tamper-proof blockchain record. Complete ownership history, legal docs, and transaction trail secured forever.', color: 'from-blue-500 to-indigo-600', glow: 'shadow-blue-500/20' },
  { icon: Cpu, title: 'AI Fraud Detection', desc: 'PropChain-FraudNet v2.1 automatically scans and verifies sale deeds, Aadhaar, and encumbrance certificates to prevent forgery.', color: 'from-purple-500 to-pink-600', glow: 'shadow-purple-500/20' },
  { icon: Users, title: 'Fractional Ownership', desc: 'Invest in a hospital or commercial tower for as little as ₹10,000. Tokenized real estate democratizes premium property investment.', color: 'from-amber-500 to-orange-600', glow: 'shadow-amber-500/20' },
  { icon: Zap, title: 'Smart Contracts', desc: 'Solidity-powered contracts automate property transfers, rental agreements, and ownership rights — no intermediaries needed.', color: 'from-emerald-500 to-teal-600', glow: 'shadow-emerald-500/20' },
]

const STATS = [
  { label: 'Properties Secured', value: '12,400+' },
  { label: 'Fraud Prevented', value: '₹840 Cr' },
  { label: 'Active Investors', value: '48,000+' },
  { label: 'Cities Covered', value: '42' },
]

const TEAM = [
  { name: 'Muruganandham Selvamani', role: 'Team Leader', grad: 'from-indigo-500 to-purple-600', photo: '/team/murugan.jpeg', linkedin: 'https://www.linkedin.com/in/muruganandham1802/' },
  { name: 'Gourav Kadu', role: 'Full Stack Developer', grad: 'from-indigo-500 to-purple-600', photo: '/team/gourav.jpeg', linkedin: 'https://www.linkedin.com/in/gourav-kadu/' },
  { name: 'Sayanto Roy', role: 'Full Stack Developer', grad: 'from-indigo-500 to-purple-600', photo: '/team/sayanto.jpeg', linkedin: 'https://www.linkedin.com/in/sayanto-roy-dev/' },
]

export default function Landing() {
  const [scrolled, setScrolled] = useState(false)
  const heroRef = useRef(null)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="min-h-screen gradient-bg text-white overflow-x-hidden">
      {/* Navbar */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'glass border-b border-white/5' : ''}`}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/40">
              <Building className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-xl">PropChain</span>
              <span className="ml-2 text-xs text-indigo-400 font-medium hidden sm:inline">by OpsAI</span>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how" className="hover:text-white transition-colors">How it Works</a>
            <a href="#stats" className="hover:text-white transition-colors">Impact</a>
            <a href="#team" className="hover:text-white transition-colors">Team</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="btn-secondary text-sm py-2 px-4">Sign In</Link>
            <Link to="/register" className="btn-primary text-sm py-2 px-4">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center px-6 pt-24" ref={heroRef}>
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse-slow delay-1000" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 glass text-indigo-300 text-sm font-medium px-4 py-2 rounded-full mb-8 border border-indigo-500/20">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            🏆 OpsAI Hackathon 2026 — Team OpsAI
          </div>

          <h1 className="text-5xl md:text-7xl font-black mb-6 leading-tight">
            <span className="bg-gradient-to-r from-white via-indigo-200 to-purple-300 bg-clip-text text-transparent">
              India's First
            </span>
            <br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Blockchain + AI
            </span>
            <br />
            <span className="text-white">Property Platform</span>
          </h1>

          <p className="text-xl text-slate-300 mb-10 max-w-3xl mx-auto leading-relaxed">
            PropChain eliminates fraud, streamlines property registration, and democratizes real estate investment
            through immutable blockchain records and AI-powered document verification.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link to="/register" className="btn-primary flex items-center gap-2 text-base px-8 py-4">
              Launch App <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/login" className="btn-secondary flex items-center gap-2 text-base px-8 py-4">
              Demo Login <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Demo credentials hint */}
          <div className="inline-flex items-center gap-3 glass rounded-xl px-6 py-3 text-sm text-slate-400 border border-white/5">
            <Lock className="w-4 h-4 text-indigo-400" />
            Demo: <span className="text-indigo-300 font-mono">demo@propchain.in</span> / <span className="text-indigo-300 font-mono">Demo@1234</span>
          </div>

          {/* Floating cards */}
          <div className="hidden lg:flex items-center justify-center gap-6 mt-16">
            {[
              { icon: '🔗', label: 'Blockchain Secured', value: '4 Blocks' },
              { icon: '🤖', label: 'AI Verified', value: '12 Properties' },
              { icon: '💎', label: 'Tokenized Assets', value: '₹5.0Bn' },
            ].map((c, i) => (
              <div key={i} className="glass-card px-6 py-4 text-center animate-float hover:border-indigo-500/30"
                style={{ animationDelay: `${i * 0.5}s` }}>
                <div className="text-2xl mb-1">{c.icon}</div>
                <div className="text-white font-bold text-sm">{c.value}</div>
                <div className="text-slate-400 text-xs">{c.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section id="stats" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map((s, i) => (
              <div key={i} className="glass-card text-center hover:border-indigo-500/30 transition-all duration-300">
                <div className="text-3xl font-black text-white mb-1">{s.value}</div>
                <div className="text-slate-400 text-sm">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 text-indigo-400 text-sm font-medium mb-4">
              <Star className="w-4 h-4" /> Core Features
            </div>
            <h2 className="text-4xl font-black text-white mb-4">Everything You Need for Secure Property Transactions</h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">A complete suite of blockchain and AI tools designed to eliminate fraud and make real estate accessible to everyone.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc, color, glow }, i) => (
              <div key={i} className={`glass-card hover:border-indigo-500/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl ${glow}`}>
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center mb-4 shadow-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{title}</h3>
                <p className="text-slate-400 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section id="how" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-black text-white mb-4">How PropChain Works</h2>
            <p className="text-slate-400 text-lg">End-to-end property registration in 4 simple steps</p>
          </div>

          <div className="grid md:grid-cols-4 gap-6 relative">
            <div className="hidden md:block absolute top-16 left-[12%] right-[12%] h-0.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 opacity-30" />
            {[
              { step: '01', title: 'Upload Documents', desc: 'Submit your sale deed, Aadhaar & encumbrance certificate' },
              { step: '02', title: 'AI Verification', desc: 'Our FraudNet AI scans and verifies document authenticity in seconds' },
              { step: '03', title: 'Blockchain Record', desc: 'Property passport is minted as an immutable block on the chain' },
              { step: '04', title: 'Ownership Confirmed', desc: 'Smart contract transfers ownership rights instantly' },
            ].map((s, i) => (
              <div key={i} className="glass-card text-center relative">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-black text-sm mx-auto mb-4 relative z-10 shadow-lg shadow-indigo-500/30">
                  {s.step}
                </div>
                <h3 className="text-white font-bold mb-2">{s.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section id="team" className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 text-indigo-400 text-sm font-medium mb-4">
            <Award className="w-4 h-4" /> The Team
          </div>
          <h2 className="text-4xl font-black text-white mb-4">Team OpsAI</h2>
          <p className="text-slate-400 text-lg mb-12">Building the future of real estate in India</p>
          
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {TEAM.map((member, i) => (
              <div key={i} className="glass-card text-center border border-indigo-500/20">
                <a href={member.linkedin} target="_blank" rel="noopener noreferrer" className="block group">
                  <div className={`p-1 rounded-2xl bg-gradient-to-br ${member.grad} w-24 h-24 mx-auto mb-4 shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200`}>
                    <img
                      src={member.photo}
                      alt={member.name}
                      className="w-full h-full object-cover rounded-xl"
                    />
                  </div>
                  <div className="text-white font-bold text-lg group-hover:text-indigo-300 transition-colors">{member.name}</div>
                </a>
                <div className="text-indigo-400 text-sm font-medium mt-1">{member.role} — OpsAI</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-black text-white text-center mb-12">Technology Stack</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { name: 'React.js', icon: '⚛️', label: 'Frontend' },
              { name: 'Python FastAPI', icon: '⚡', label: 'Backend' },
              { name: 'Ethereum', icon: '💎', label: 'Blockchain' },
              { name: 'TensorFlow', icon: '🧠', label: 'AI/ML' },
              { name: 'Solidity', icon: '📜', label: 'Smart Contracts' },
              { name: 'MongoDB', icon: '🗄️', label: 'Database' },
            ].map((t, i) => (
              <div key={i} className="glass-card text-center hover:border-indigo-500/30 transition-all hover:-translate-y-1">
                <div className="text-3xl mb-2">{t.icon}</div>
                <div className="text-white text-sm font-semibold">{t.name}</div>
                <div className="text-slate-500 text-xs mt-1">{t.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="glass-card border border-indigo-500/20 py-16">
            <h2 className="text-4xl font-black text-white mb-4">Ready to Secure Your Property?</h2>
            <p className="text-slate-400 text-lg mb-8">Join thousands of property owners who trust PropChain for transparent, fraud-proof real estate transactions.</p>
            <Link to="/register" className="btn-primary inline-flex items-center gap-2 text-lg px-10 py-4">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 px-6 text-center text-slate-500 text-sm">
        <p>© 2026 PropChain by OpsAI | Team OpsAI: Muruganandham Selvamani · Gourav Kadu · Sayanto Roy | Built for Hackathon 2026</p>
        <p className="mt-2 text-xs">Powered by Ethereum · Python FastAPI · React.js · TensorFlow/AI</p>
      </footer>
    </div>
  )
}
