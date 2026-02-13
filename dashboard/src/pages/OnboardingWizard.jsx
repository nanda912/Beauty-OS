import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StepIndicator from '../components/StepIndicator'

const API_BASE = '/api'

function apiHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': localStorage.getItem('beautyos_api_key') || '',
  }
}

// ── Step 1: Services ────────────────────────────────────────────────

function ServicesStep({ services, setServices, onNext }) {
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [duration, setDuration] = useState('')
  const [adding, setAdding] = useState(false)

  async function addService(e) {
    e.preventDefault()
    setAdding(true)
    try {
      const res = await fetch(`${API_BASE}/onboarding/services`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ name, price: parseFloat(price), duration_min: parseInt(duration) }),
      })
      const data = await res.json()
      setServices([...services, data])
      setName(''); setPrice(''); setDuration('')
    } catch (err) {
      alert('Failed to add service')
    }
    setAdding(false)
  }

  async function removeService(id) {
    await fetch(`${API_BASE}/onboarding/services/${id}`, { method: 'DELETE', headers: apiHeaders() })
    setServices(services.filter(s => s.id !== id))
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-bold text-brand-charcoal mb-2">
        What services do you offer?
      </h2>
      <p className="text-brand-charcoal/50 mb-6">Add your services with prices and how long they take.</p>

      {/* Service list */}
      {services.length > 0 && (
        <div className="space-y-2 mb-6">
          {services.map(s => (
            <div key={s.id} className="flex items-center justify-between bg-brand-pink-light/50 rounded-xl px-4 py-3">
              <div>
                <span className="font-medium text-brand-charcoal">{s.name}</span>
                <span className="text-brand-charcoal/50 ml-2">
                  ${s.price} · {s.duration_min} min
                </span>
              </div>
              <button onClick={() => removeService(s.id)} className="text-brand-pink-dark hover:text-red-500 text-sm">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      <form onSubmit={addService} className="grid grid-cols-12 gap-3 mb-8">
        <input
          type="text"
          required
          placeholder="Service name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="col-span-5 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
        />
        <input
          type="number"
          required
          step="0.01"
          min="0"
          placeholder="Price $"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className="col-span-3 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
        />
        <input
          type="number"
          required
          min="1"
          placeholder="Min"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          className="col-span-2 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
        />
        <button
          type="submit"
          disabled={adding}
          className="col-span-2 py-3 bg-brand-charcoal text-white rounded-xl font-medium hover:bg-brand-charcoal/90 transition disabled:opacity-50 text-sm"
        >
          {adding ? '...' : '+ Add'}
        </button>
      </form>

      <button
        onClick={onNext}
        disabled={services.length === 0}
        className="w-full py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-30"
      >
        Next: Add-Ons →
      </button>
    </div>
  )
}

// ── Step 2: Add-Ons ─────────────────────────────────────────────────

function AddOnsStep({ services, onNext, onBack }) {
  const [selectedService, setSelectedService] = useState(services[0]?.id || '')
  const [addons, setAddons] = useState({})
  const [form, setForm] = useState({ name: '', price: '', duration_min: '', pitch: '' })
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    // Load existing addons for each service
    services.forEach(async (svc) => {
      const res = await fetch(`${API_BASE}/onboarding/addons/${svc.id}`, { headers: apiHeaders() })
      const data = await res.json()
      setAddons(prev => ({ ...prev, [svc.id]: data }))
    })
  }, [services])

  async function addAddon(e) {
    e.preventDefault()
    setAdding(true)
    try {
      const res = await fetch(`${API_BASE}/onboarding/addons`, {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          service_id: selectedService,
          name: form.name,
          price: parseFloat(form.price),
          duration_min: parseInt(form.duration_min),
          pitch: form.pitch,
        }),
      })
      const data = await res.json()
      setAddons(prev => ({
        ...prev,
        [selectedService]: [...(prev[selectedService] || []), data],
      }))
      setForm({ name: '', price: '', duration_min: '', pitch: '' })
    } catch (err) {
      alert('Failed to add add-on')
    }
    setAdding(false)
  }

  async function removeAddon(addonId, serviceId) {
    await fetch(`${API_BASE}/onboarding/addons/${addonId}`, { method: 'DELETE', headers: apiHeaders() })
    setAddons(prev => ({
      ...prev,
      [serviceId]: (prev[serviceId] || []).filter(a => a.id !== addonId),
    }))
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-bold text-brand-charcoal mb-2">
        Found Money Add-Ons
      </h2>
      <p className="text-brand-charcoal/50 mb-6">
        Add high-margin upsells to each service. The Revenue Engine texts clients 24h before their appointment with a cheeky pitch — turning a $65 wax into an $80 ticket automatically.
      </p>

      {/* Service selector */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {services.map(svc => (
          <button
            key={svc.id}
            onClick={() => setSelectedService(svc.id)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition ${
              selectedService === svc.id
                ? 'bg-brand-charcoal text-white'
                : 'bg-brand-pink-light text-brand-charcoal/60 hover:bg-brand-pink'
            }`}
          >
            {svc.name}
          </button>
        ))}
      </div>

      {/* Current addons for selected service */}
      {(addons[selectedService] || []).length > 0 && (
        <div className="space-y-2 mb-4">
          {(addons[selectedService] || []).map(a => (
            <div key={a.id} className="flex items-center justify-between bg-brand-gold/5 rounded-xl px-4 py-3">
              <div>
                <span className="font-medium text-brand-charcoal">{a.name}</span>
                <span className="text-brand-charcoal/50 ml-2">${a.price}</span>
                {a.pitch && <p className="text-xs text-brand-charcoal/40 mt-0.5">"{a.pitch}"</p>}
              </div>
              <button onClick={() => removeAddon(a.id, selectedService)} className="text-brand-pink-dark hover:text-red-500 text-sm">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      <form onSubmit={addAddon} className="space-y-3 mb-8">
        <div className="grid grid-cols-12 gap-3">
          <input
            type="text"
            required
            placeholder="Add-on name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="col-span-5 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <input
            type="number"
            required
            step="0.01"
            min="0"
            placeholder="Price $"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
            className="col-span-3 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <input
            type="number"
            required
            min="1"
            placeholder="Min"
            value={form.duration_min}
            onChange={(e) => setForm({ ...form, duration_min: e.target.value })}
            className="col-span-2 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <button
            type="submit"
            disabled={adding}
            className="col-span-2 py-3 bg-brand-charcoal text-white rounded-xl font-medium hover:bg-brand-charcoal/90 transition disabled:opacity-50 text-sm"
          >
            {adding ? '...' : '+ Add'}
          </button>
        </div>
        <input
          type="text"
          placeholder="Pitch line (e.g., 'Add a quick nose wax while you're here')"
          value={form.pitch}
          onChange={(e) => setForm({ ...form, pitch: e.target.value })}
          className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
        />
      </form>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 py-3 border border-brand-pink/30 text-brand-charcoal rounded-xl font-medium hover:bg-brand-pink-light/50 transition">
          ← Back
        </button>
        <button onClick={onNext} className="flex-1 py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition">
          Next: Policies →
        </button>
      </div>
    </div>
  )
}

// ── Step 3: Policies ────────────────────────────────────────────────

function PoliciesStep({ onNext, onBack }) {
  const [policies, setPolicies] = useState({
    deposit_amount: 25,
    late_fee: 15,
    cancel_window_hours: 24,
    booking_url: '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/onboarding/policies`, { headers: apiHeaders() })
      .then(r => r.json())
      .then(data => setPolicies(data))
      .catch(() => {})
  }, [])

  async function savePolicies() {
    setSaving(true)
    await fetch(`${API_BASE}/onboarding/policies`, {
      method: 'PUT',
      headers: apiHeaders(),
      body: JSON.stringify(policies),
    })
    setSaving(false)
    onNext()
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-bold text-brand-charcoal mb-2">
        Your Policies
      </h2>
      <p className="text-brand-charcoal/50 mb-6">
        The AI will enforce these rules with every client — no exceptions.
      </p>

      <div className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">
            Deposit Amount ($)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={policies.deposit_amount}
            onChange={(e) => setPolicies({ ...policies, deposit_amount: parseFloat(e.target.value) || 0 })}
            className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <p className="text-xs text-brand-charcoal/40 mt-1">Non-refundable deposit required to book.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">
            Late Fee ($)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={policies.late_fee}
            onChange={(e) => setPolicies({ ...policies, late_fee: parseFloat(e.target.value) || 0 })}
            className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <p className="text-xs text-brand-charcoal/40 mt-1">Applied for arrivals 5-14 minutes late.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">
            Cancellation Window (hours)
          </label>
          <input
            type="number"
            min="1"
            value={policies.cancel_window_hours}
            onChange={(e) => setPolicies({ ...policies, cancel_window_hours: parseInt(e.target.value) || 24 })}
            className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <p className="text-xs text-brand-charcoal/40 mt-1">Cancellations within this window forfeit the deposit.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">
            Booking URL
          </label>
          <input
            type="url"
            placeholder="https://yourbookingpage.com"
            value={policies.booking_url}
            onChange={(e) => setPolicies({ ...policies, booking_url: e.target.value })}
            className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          />
          <p className="text-xs text-brand-charcoal/40 mt-1">The AI sends this link once a client passes screening.</p>
        </div>
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 py-3 border border-brand-pink/30 text-brand-charcoal rounded-xl font-medium hover:bg-brand-pink-light/50 transition">
          ← Back
        </button>
        <button
          onClick={savePolicies}
          disabled={saving}
          className="flex-1 py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Next: Brand Voice →'}
        </button>
      </div>
    </div>
  )
}

// ── Step 4: Brand Voice ─────────────────────────────────────────────

const VOICE_OPTIONS = [
  {
    key: 'professional_chill',
    label: 'Professional & Chill',
    desc: 'Warm but firm. You enforce rules without breaking a sweat.',
    emoji: '😎',
    example: '"Hey girl! Before I get you booked, just a heads up — we require a $25 non-refundable deposit. Totally understand if that works for you!"',
  },
  {
    key: 'warm_bubbly',
    label: 'Warm & Bubbly',
    desc: 'Excited, positive energy. Makes everyone feel like a VIP.',
    emoji: '🥰',
    example: '"OMG hi!! I\'d love to get you in! Quick thing — we do a $25 deposit to hold your spot (it goes toward your service!). Sound good? 💕"',
  },
  {
    key: 'luxury_exclusive',
    label: 'Luxury & Exclusive',
    desc: 'Polished, refined. Policies are "standards of our house."',
    emoji: '✨',
    example: '"Thank you for your interest. We maintain a $25 deposit as part of our booking standards. Shall I proceed with scheduling your appointment?"',
  },
]

function BrandVoiceStep({ onNext, onBack }) {
  const [selected, setSelected] = useState('professional_chill')
  const [saving, setSaving] = useState(false)

  async function saveVoice() {
    setSaving(true)
    await fetch(`${API_BASE}/onboarding/brand-voice`, {
      method: 'PUT',
      headers: apiHeaders(),
      body: JSON.stringify({ brand_voice: selected }),
    })
    setSaving(false)
    onNext()
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-bold text-brand-charcoal mb-2">
        Pick Your Vibe
      </h2>
      <p className="text-brand-charcoal/50 mb-6">
        How should your AI assistant sound when talking to clients?
      </p>

      <div className="space-y-3 mb-8">
        {VOICE_OPTIONS.map(v => (
          <button
            key={v.key}
            onClick={() => setSelected(v.key)}
            className={`w-full text-left p-5 rounded-2xl border-2 transition ${
              selected === v.key
                ? 'border-brand-gold bg-brand-gold/5'
                : 'border-brand-pink/20 hover:border-brand-pink/40'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{v.emoji}</span>
              <span className="font-display font-bold text-brand-charcoal">{v.label}</span>
              {selected === v.key && (
                <span className="ml-auto text-brand-gold text-sm font-medium">Selected</span>
              )}
            </div>
            <p className="text-sm text-brand-charcoal/60 mb-2">{v.desc}</p>
            <div className="bg-white rounded-xl p-3 text-sm text-brand-charcoal/70 italic border border-brand-pink/10">
              {v.example}
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 py-3 border border-brand-pink/30 text-brand-charcoal rounded-xl font-medium hover:bg-brand-pink-light/50 transition">
          ← Back
        </button>
        <button
          onClick={saveVoice}
          disabled={saving}
          className="flex-1 py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Next: Live Demo →'}
        </button>
      </div>
    </div>
  )
}

// ── Step 5: Live Demo ───────────────────────────────────────────────

function LiveDemoStep({ onBack }) {
  const navigate = useNavigate()
  const slug = localStorage.getItem('beautyos_slug') || ''
  const studioName = localStorage.getItem('beautyos_studio_name') || 'Your Studio'

  const [messages, setMessages] = useState([
    { role: 'system', text: `Hi! I'm the AI Gatekeeper for ${studioName}. When the Social Hunter spots a ready-to-buy lead, I screen them like this. Try sending a message as a potential client!` },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [finishing, setFinishing] = useState(false)

  const EXAMPLE_PROMPTS = [
    "Hey! I want to book a Brazilian wax for next Saturday. What times do you have?",
    "How much for a bikini wax? Can I get a discount?",
    "I need an appointment NOW. I don't care about your deposit.",
  ]

  async function sendMessage(text) {
    const msg = text || input
    if (!msg.trim()) return

    setMessages(prev => [...prev, { role: 'user', text: msg }])
    setInput('')
    setLoading(true)

    const maxRetries = 3
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const res = await fetch(`${API_BASE}/onboarding/demo`, {
          method: 'POST',
          headers: apiHeaders(),
          body: JSON.stringify({ message: msg, sender_name: 'Demo Client' }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setMessages(prev => [...prev, {
          role: 'ai',
          text: data.draft_reply,
          meta: {
            vibe_score: data.vibe_score,
            is_approved: data.is_approved,
            detected_intent: data.detected_intent,
          },
        }])
        setLoading(false)
        return
      } catch (err) {
        if (attempt < maxRetries - 1) {
          await new Promise(r => setTimeout(r, 1500 * (attempt + 1)))
        }
      }
    }
    setMessages(prev => [...prev, { role: 'ai', text: 'Hmm, the AI is warming up. Give it one more try!' }])
    setLoading(false)
  }

  async function finishOnboarding() {
    setFinishing(true)
    await fetch(`${API_BASE}/onboarding/complete`, {
      method: 'POST',
      headers: apiHeaders(),
    })
    navigate(`/dashboard/${slug}`)
  }

  return (
    <div>
      <h2 className="text-2xl font-display font-bold text-brand-charcoal mb-2">
        See Your AI in Action
      </h2>
      <p className="text-brand-charcoal/50 mb-4">
        The Social Hunter listens across social platforms and sends leads here. The Gatekeeper screens them using YOUR services, policies, and voice. Try it!
      </p>

      {/* Example prompts */}
      <div className="flex flex-wrap gap-2 mb-4">
        {EXAMPLE_PROMPTS.map((p, i) => (
          <button
            key={i}
            onClick={() => sendMessage(p)}
            disabled={loading}
            className="text-xs px-3 py-1.5 bg-brand-pink-light text-brand-charcoal/70 rounded-full hover:bg-brand-pink transition disabled:opacity-50"
          >
            {p.slice(0, 40)}...
          </button>
        ))}
      </div>

      {/* Chat window */}
      <div className="bg-white border border-brand-pink/20 rounded-2xl p-4 h-80 overflow-y-auto mb-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-brand-charcoal text-white'
                : msg.role === 'system'
                ? 'bg-brand-gold/10 text-brand-charcoal'
                : 'bg-brand-pink-light text-brand-charcoal'
            }`}>
              <p className="text-sm">{msg.text}</p>
              {msg.meta && (
                <div className="mt-2 pt-2 border-t border-brand-pink/20 flex gap-3 text-xs text-brand-charcoal/50">
                  <span>Vibe: {(msg.meta.vibe_score * 100).toFixed(0)}%</span>
                  <span>{msg.meta.is_approved ? '✅ Approved' : '❌ Filtered'}</span>
                  <span>{msg.meta.detected_intent}</span>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-brand-pink-light rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-brand-charcoal/30 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-brand-charcoal/30 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-brand-charcoal/30 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={(e) => { e.preventDefault(); sendMessage() }} className="flex gap-3 mb-6">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message like a real DM..."
          className="flex-1 px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-3 bg-brand-charcoal text-white rounded-xl font-medium hover:bg-brand-charcoal/90 transition disabled:opacity-50"
        >
          Send
        </button>
      </form>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 py-3 border border-brand-pink/30 text-brand-charcoal rounded-xl font-medium hover:bg-brand-pink-light/50 transition">
          ← Back
        </button>
        <button
          onClick={finishOnboarding}
          disabled={finishing}
          className="flex-1 py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
        >
          {finishing ? 'Activating...' : 'Activate & Start Growing →'}
        </button>
      </div>
    </div>
  )
}

// ── Main Wizard ─────────────────────────────────────────────────────

export default function OnboardingWizard() {
  const { slug } = useParams()
  const [step, setStep] = useState(1)
  const [services, setServices] = useState([])

  // Load existing services on mount
  useEffect(() => {
    fetch(`${API_BASE}/onboarding/services`, { headers: apiHeaders() })
      .then(r => r.ok ? r.json() : [])
      .then(data => { if (Array.isArray(data)) setServices(data) })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-cream via-white to-brand-pink-light">
      {/* Header */}
      <header className="border-b border-brand-pink/20 bg-white/80 backdrop-blur-sm">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-display font-bold text-brand-charcoal">
            Beauty <span className="text-brand-gold">OS</span>
          </h1>
          <span className="text-sm text-brand-charcoal/40">
            Setting up: {localStorage.getItem('beautyos_studio_name') || slug}
          </span>
        </div>
      </header>

      {/* Wizard Content */}
      <main className="max-w-2xl mx-auto px-6 py-8">
        <StepIndicator current={step} />

        {step === 1 && (
          <ServicesStep
            services={services}
            setServices={setServices}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <AddOnsStep
            services={services}
            onNext={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <PoliciesStep
            onNext={() => setStep(4)}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && (
          <BrandVoiceStep
            onNext={() => setStep(5)}
            onBack={() => setStep(3)}
          />
        )}
        {step === 5 && (
          <LiveDemoStep
            onBack={() => setStep(4)}
          />
        )}
      </main>
    </div>
  )
}
