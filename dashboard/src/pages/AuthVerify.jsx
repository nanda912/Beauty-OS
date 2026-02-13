import React, { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'

const API_BASE = '/api'

export default function AuthVerify() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState('verifying') // verifying | success | error
  const [error, setError] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setStatus('error')
      setError('No token provided. Please request a new sign-in link.')
      return
    }

    async function verify() {
      try {
        const res = await fetch(`${API_BASE}/auth/verify-magic-link`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || 'Invalid or expired link.')
        }

        const data = await res.json()

        // Store credentials in localStorage (same as registration flow)
        localStorage.setItem('beautyos_api_key', data.api_key)
        localStorage.setItem('beautyos_slug', data.slug)
        localStorage.setItem('beautyos_studio_name', data.name)

        setStatus('success')

        // Redirect to dashboard after a brief moment
        setTimeout(() => {
          navigate(`/dashboard/${data.slug}`)
        }, 1500)
      } catch (err) {
        setStatus('error')
        setError(err.message || 'Something went wrong. Please request a new sign-in link.')
      }
    }

    verify()
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-cream via-white to-brand-pink-light flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl text-center">
        <Link to="/">
          <h1 className="text-2xl font-display font-bold text-brand-charcoal mb-8">
            Beauty <span className="text-brand-gold">OS</span>
          </h1>
        </Link>

        {status === 'verifying' && (
          <>
            <div className="w-16 h-16 bg-brand-gold/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <div className="w-8 h-8 border-3 border-brand-gold/30 border-t-brand-gold rounded-full animate-spin" />
            </div>
            <h2 className="text-xl font-display font-bold text-brand-charcoal mb-2">
              Signing you in...
            </h2>
            <p className="text-sm text-brand-charcoal/50">
              Verifying your magic link.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <h2 className="text-xl font-display font-bold text-brand-charcoal mb-2">
              You're in!
            </h2>
            <p className="text-sm text-brand-charcoal/50">
              Redirecting to your dashboard...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <h2 className="text-xl font-display font-bold text-brand-charcoal mb-2">
              Link expired or invalid
            </h2>
            <p className="text-sm text-brand-charcoal/50 mb-6">
              {error}
            </p>
            <Link
              to="/login"
              className="inline-flex px-6 py-3 bg-brand-gold text-white rounded-xl font-semibold hover:bg-brand-gold-dark transition"
            >
              Request a New Link
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
