import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'

const API_BASE = '/api'

export default function LandingPage() {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ name: '', owner_name: '', email: '', phone: '', ig_handle: '' })
  const [regError, setRegError] = useState('')

  async function handleRegister(e) {
    e.preventDefault()
    setLoading(true)
    setRegError('')
    try {
      const res = await fetch(`${API_BASE}/onboarding/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.status === 409) {
        setRegError('An account with this email already exists.')
        setLoading(false)
        return
      }
      if (!res.ok) throw new Error('Registration failed')
      const data = await res.json()
      localStorage.setItem('beautyos_api_key', data.api_key)
      localStorage.setItem('beautyos_slug', data.slug)
      localStorage.setItem('beautyos_studio_name', data.name)
      navigate(`/onboard/${data.slug}`)
    } catch (err) {
      setRegError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-cream via-white to-brand-pink-light">
      {/* Nav */}
      <nav className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-brand-charcoal">
          Beauty <span className="text-brand-gold">OS</span>
        </h1>
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="px-4 py-2 text-brand-charcoal/60 text-sm font-medium hover:text-brand-charcoal transition"
          >
            Sign In
          </Link>
          <button
            onClick={() => setShowForm(true)}
            className="px-5 py-2 bg-brand-charcoal text-white rounded-full text-sm font-medium hover:bg-brand-charcoal/90 transition"
          >
            Start My Growth Engine
          </button>
        </div>
      </nav>

      {/* Hero */}
      <main className="max-w-6xl mx-auto px-6 pt-16 pb-24">
        <div className="text-center max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-brand-gold/10 rounded-full text-brand-gold-dark text-sm font-medium mb-8">
            <span className="w-2 h-2 bg-brand-gold rounded-full animate-pulse" />
            AI-Powered Client Acquisition
          </div>

          <h2 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold text-brand-charcoal leading-tight mb-6">
            The AI That Finds and Books{' '}
            <span className="text-brand-gold">Your Clients — 24/7</span>
          </h2>

          <p className="text-lg text-brand-charcoal/60 mb-10 max-w-2xl mx-auto">
            Done chasing DMs and hoping for referrals. Beauty OS listens across social
            platforms, screens every lead for brand fit, secures deposits, and fills
            your calendar — so you never market yourself again.
          </p>

          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-8 py-4 bg-brand-gold text-white rounded-full text-lg font-semibold hover:bg-brand-gold-dark transition shadow-lg shadow-brand-gold/25"
          >
            Start My Growth Engine
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>

          <p className="mt-4 text-sm text-brand-charcoal/40">
            5-minute setup. No marketing experience needed.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mt-20">
          {[
            {
              title: 'The Social Hunter',
              desc: 'High-frequency social listening across Instagram, Nextdoor, and Reddit. Spots ready-to-buy locals, starts a conversation, and moves them from social post to paid deposit — all before you wake up.',
              icon: '🎯',
              tag: 'NEW CLIENTS',
            },
            {
              title: 'The Gatekeeper',
              desc: 'Protects your time and your brand. Screens every lead the Hunter finds for vibe fit, enforces your deposit policy, and only lets dream clients touch your calendar.',
              icon: '🛡️',
              tag: 'QUALITY CONTROL',
            },
            {
              title: 'The Revenue Engine',
              desc: 'Found money on autopilot. Sends cheeky, personalized SMS upsells 24 hours before every appointment — turning a $65 wax into an $80 ticket with a quick nose wax add-on.',
              icon: '💰',
              tag: 'FOUND MONEY',
            },
            {
              title: 'Growth Analytics',
              desc: 'See exactly how your AI is growing your business — new clients acquired, total found money from upsells, and administrative hours reclaimed.',
              icon: '📈',
              tag: 'TRACK GROWTH',
            },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-2xl p-6 border border-brand-pink/20 shadow-sm hover:shadow-md transition group">
              <div className="flex items-center justify-between mb-3">
                <span className="text-3xl">{f.icon}</span>
                <span className="text-[10px] font-bold tracking-wider text-brand-gold bg-brand-gold/10 px-2 py-0.5 rounded-full">
                  {f.tag}
                </span>
              </div>
              <h3 className="font-display font-bold text-brand-charcoal mb-2">{f.title}</h3>
              <p className="text-sm text-brand-charcoal/60 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* Social Proof / How It Works */}
        <div className="mt-20 text-center">
          <h3 className="text-2xl font-display font-bold text-brand-charcoal mb-8">
            How It Works
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl mx-auto">
            {[
              { step: '1', title: 'Set Up Your Studio', desc: 'Add your services, prices, policies, and pick your brand voice.' },
              { step: '2', title: 'AI Starts Listening', desc: 'The Social Hunter scans Instagram, Nextdoor, and Reddit for ready-to-buy locals — the Gatekeeper screens them instantly.' },
              { step: '3', title: 'Watch Your Calendar Fill', desc: 'Qualified, deposit-secured clients show up. You just do what you love.' },
            ].map((s) => (
              <div key={s.step} className="text-center">
                <div className="w-12 h-12 rounded-full bg-brand-gold/10 text-brand-gold font-display font-bold text-xl flex items-center justify-center mx-auto mb-3">
                  {s.step}
                </div>
                <h4 className="font-display font-bold text-brand-charcoal mb-1">{s.title}</h4>
                <p className="text-sm text-brand-charcoal/50">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-20 text-center">
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-8 py-4 bg-brand-charcoal text-white rounded-full text-lg font-semibold hover:bg-brand-charcoal/90 transition"
          >
            Start My Growth Engine
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
          <p className="mt-3 text-sm text-brand-charcoal/40">
            No credit card. No contracts. Just clients.
          </p>
        </div>
      </main>

      {/* Registration Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-xl font-display font-bold text-brand-charcoal">
                  Start Growing Your Studio
                </h3>
                <p className="text-sm text-brand-charcoal/50 mt-1">5 minutes to set up. Clients start coming in today.</p>
              </div>
              <button onClick={() => setShowForm(false)} className="text-brand-charcoal/40 hover:text-brand-charcoal">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">Studio Name *</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g., Nails by Nina"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">Your Name *</label>
                <input
                  type="text"
                  required
                  value={form.owner_name}
                  onChange={(e) => setForm({ ...form, owner_name: e.target.value })}
                  placeholder="e.g., Nina Martinez"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
                <p className="text-xs text-brand-charcoal/40 mt-1">For signing back in later</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">Phone</label>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="(555) 123-4567"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">Instagram Handle</label>
                <input
                  type="text"
                  value={form.ig_handle}
                  onChange={(e) => setForm({ ...form, ig_handle: e.target.value })}
                  placeholder="@nailsbynina"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
              </div>

              {regError && (
                <p className="text-sm text-red-500">{regError}{' '}
                  {regError.includes('already exists') && (
                    <Link to="/login" className="text-brand-gold hover:text-brand-gold-dark font-medium underline">
                      Sign in here
                    </Link>
                  )}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Start My Growth Engine'}
              </button>

              <p className="text-center text-sm text-brand-charcoal/40">
                Already have an account?{' '}
                <Link to="/login" className="text-brand-gold hover:text-brand-gold-dark font-medium">
                  Sign in
                </Link>
              </p>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
