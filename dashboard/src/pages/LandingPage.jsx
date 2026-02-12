import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = '/api'

export default function LandingPage() {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ name: '', owner_name: '', phone: '', ig_handle: '' })

  async function handleRegister(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/onboarding/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error('Registration failed')
      const data = await res.json()
      // Store API key for subsequent requests
      localStorage.setItem('beautyos_api_key', data.api_key)
      localStorage.setItem('beautyos_slug', data.slug)
      localStorage.setItem('beautyos_studio_name', data.name)
      navigate(`/onboard/${data.slug}`)
    } catch (err) {
      alert('Something went wrong. Please try again.')
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
        <button
          onClick={() => setShowForm(true)}
          className="px-5 py-2 bg-brand-charcoal text-white rounded-full text-sm font-medium hover:bg-brand-charcoal/90 transition"
        >
          Sign Up Free
        </button>
      </nav>

      {/* Hero */}
      <main className="max-w-6xl mx-auto px-6 pt-16 pb-24">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-brand-gold/10 rounded-full text-brand-gold-dark text-sm font-medium mb-8">
            <span className="w-2 h-2 bg-brand-gold rounded-full animate-pulse" />
            AI-Powered Studio Management
          </div>

          <h2 className="text-5xl md:text-6xl font-display font-bold text-brand-charcoal leading-tight mb-6">
            Your AI Studio Manager,{' '}
            <span className="text-brand-gold">Working 24/7</span>
          </h2>

          <p className="text-lg text-brand-charcoal/60 mb-10 max-w-2xl mx-auto">
            Screen clients, upsell add-ons, fill cancellations, and track revenue —
            all on autopilot. Set up in 5 minutes, no coding required.
          </p>

          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-8 py-4 bg-brand-gold text-white rounded-full text-lg font-semibold hover:bg-brand-gold-dark transition shadow-lg shadow-brand-gold/25"
          >
            Get Started Free
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mt-20">
          {[
            {
              title: 'Vibe Check',
              desc: 'AI screens every DM for brand fit and enforces your deposit policy.',
              icon: '🛡️',
            },
            {
              title: 'Revenue Engine',
              desc: 'Sends personalized upsell texts 24h before every appointment.',
              icon: '💰',
            },
            {
              title: 'Gap Filler',
              desc: 'Auto-notifies your waitlist the second a slot opens up.',
              icon: '📅',
            },
            {
              title: 'BI Dashboard',
              desc: 'See your found money, hours saved, and conversion rates live.',
              icon: '📊',
            },
          ].map((f) => (
            <div key={f.title} className="bg-white rounded-2xl p-6 border border-brand-pink/20 shadow-sm hover:shadow-md transition">
              <span className="text-3xl">{f.icon}</span>
              <h3 className="font-display font-bold text-brand-charcoal mt-3 mb-2">{f.title}</h3>
              <p className="text-sm text-brand-charcoal/60">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Registration Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-display font-bold text-brand-charcoal">
                Create Your Studio
              </h3>
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

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Studio & Start Setup'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
