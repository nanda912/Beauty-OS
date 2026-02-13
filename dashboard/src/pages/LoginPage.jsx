import React, { useState } from 'react'
import { Link } from 'react-router-dom'

const API_BASE = '/api'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/auth/send-magic-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!res.ok) throw new Error('Failed to send')
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-cream via-white to-brand-pink-light flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
        {/* Logo */}
        <Link to="/">
          <h1 className="text-2xl font-display font-bold text-brand-charcoal mb-1">
            Beauty <span className="text-brand-gold">OS</span>
          </h1>
        </Link>

        {!sent ? (
          <>
            <h2 className="text-xl font-display font-bold text-brand-charcoal mt-6 mb-2">
              Welcome back
            </h2>
            <p className="text-sm text-brand-charcoal/50 mb-6">
              Enter your email and we'll send you a sign-in link.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-brand-charcoal/70 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-4 py-3 border border-brand-pink/30 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-gold/50 focus:border-brand-gold"
                />
              </div>

              {error && (
                <p className="text-sm text-red-500">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Sign-In Link'}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-brand-charcoal/40">
              Don't have an account?{' '}
              <Link to="/" className="text-brand-gold hover:text-brand-gold-dark font-medium">
                Get started
              </Link>
            </p>
          </>
        ) : (
          <div className="text-center mt-6">
            <div className="w-16 h-16 bg-brand-gold/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-brand-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
            </div>
            <h2 className="text-xl font-display font-bold text-brand-charcoal mb-2">
              Check your inbox
            </h2>
            <p className="text-sm text-brand-charcoal/50 mb-6">
              We sent a sign-in link to <strong className="text-brand-charcoal">{email}</strong>.
              <br />It expires in 15 minutes.
            </p>
            <button
              onClick={() => { setSent(false); setError('') }}
              className="text-sm text-brand-gold hover:text-brand-gold-dark font-medium"
            >
              Try a different email
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
