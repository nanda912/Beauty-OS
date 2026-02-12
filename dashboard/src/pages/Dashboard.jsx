import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'

const API_BASE = '/api'

async function fetchDashboard(slug) {
  try {
    const url = slug ? `${API_BASE}/dashboard/${slug}` : `${API_BASE}/dashboard`
    const res = await fetch(url)
    if (!res.ok) throw new Error('API error')
    return await res.json()
  } catch {
    return {
      found_money: 0,
      ai_chats: 0,
      hours_reclaimed: 0,
      leads_approved: 0,
      leads_filtered: 0,
      gap_fills: 0,
    }
  }
}

// ── Icon Components ─────────────────────────────────────────────────

function DollarIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  )
}

function CalendarIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
    </svg>
  )
}

// ── Stat Card ───────────────────────────────────────────────────────

function StatCard({ icon, label, value, subtext, accent = false }) {
  return (
    <div className={`rounded-2xl p-6 shadow-sm border transition-all duration-200 hover:shadow-md ${
      accent
        ? 'bg-gradient-to-br from-brand-gold/10 to-brand-gold/5 border-brand-gold/20'
        : 'bg-white border-brand-pink/20'
    }`}>
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2.5 rounded-xl ${
          accent ? 'bg-brand-gold/15 text-brand-gold-dark' : 'bg-brand-pink-light text-brand-pink-dark'
        }`}>
          {icon}
        </div>
        <span className="text-sm font-medium text-brand-charcoal/60 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <div className="text-3xl font-bold font-display text-brand-charcoal">
        {value}
      </div>
      {subtext && (
        <p className="mt-1.5 text-sm text-brand-charcoal/50">{subtext}</p>
      )}
    </div>
  )
}

// ── Vibe Check Breakdown ────────────────────────────────────────────

function VibeCheckBar({ approved, filtered }) {
  const total = approved + filtered
  const approvedPct = total > 0 ? (approved / total) * 100 : 0

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-brand-pink/20">
      <h3 className="text-sm font-medium text-brand-charcoal/60 uppercase tracking-wide mb-4">
        Vibe Check Stats
      </h3>
      <div className="flex items-end justify-between mb-3">
        <div>
          <span className="text-2xl font-bold font-display">{approved}</span>
          <span className="text-sm text-brand-charcoal/50 ml-1">approved</span>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold font-display text-brand-pink-dark">{filtered}</span>
          <span className="text-sm text-brand-charcoal/50 ml-1">filtered</span>
        </div>
      </div>
      <div className="h-3 bg-brand-pink-light rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-gold to-brand-gold-light rounded-full transition-all duration-700"
          style={{ width: `${approvedPct}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-brand-charcoal/40">
        {total > 0 ? `${approvedPct.toFixed(0)}% conversion rate` : 'No leads yet'} — your gatekeeper is working
      </p>
    </div>
  )
}

// ── Activity Feed ───────────────────────────────────────────────────

function ActivityFeed() {
  const activities = [
    { time: 'Just now', text: 'Dashboard loaded — all systems active', type: 'booking' },
  ]

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-brand-pink/20">
      <h3 className="text-sm font-medium text-brand-charcoal/60 uppercase tracking-wide mb-4">
        Recent Activity
      </h3>
      <div className="space-y-3">
        {activities.map((a, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
              a.type === 'revenue' ? 'bg-brand-gold' :
              a.type === 'filter' ? 'bg-brand-pink-dark' :
              a.type === 'gap' ? 'bg-emerald-500' : 'bg-blue-500'
            }`} />
            <span className="text-sm text-brand-charcoal/80 flex-1">{a.text}</span>
            <span className="text-xs text-brand-charcoal/40 flex-shrink-0">{a.time}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Dashboard ──────────────────────────────────────────────────

export default function Dashboard() {
  const { slug } = useParams()
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboard(slug).then((data) => {
      setMetrics(data)
      setLoading(false)
    })
  }, [slug])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-cream">
        <div className="animate-pulse text-brand-gold font-display text-2xl">
          Loading Beauty OS...
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-brand-cream">
      {/* Header */}
      <header className="border-b border-brand-pink/20 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/">
            <h1 className="text-2xl font-display font-bold text-brand-charcoal">
              Beauty <span className="text-brand-gold">OS</span>
            </h1>
            <p className="text-xs text-brand-charcoal/40 tracking-wide uppercase">
              {slug ? slug.replace(/-/g, ' ') : 'Studio Dashboard'}
            </p>
          </Link>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              All Systems Active
            </span>
          </div>
        </div>
      </header>

      {/* Dashboard Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <StatCard
            icon={<DollarIcon />}
            label="Found Money"
            value={`$${metrics.found_money.toLocaleString()}`}
            subtext="Revenue from automated upsells"
            accent
          />
          <StatCard
            icon={<ClockIcon />}
            label="Hours Reclaimed"
            value={`${metrics.hours_reclaimed}h`}
            subtext={`${metrics.ai_chats} AI-handled conversations`}
          />
          <StatCard
            icon={<ShieldIcon />}
            label="Leads Screened"
            value={metrics.leads_approved + metrics.leads_filtered}
            subtext={`${metrics.leads_filtered} filtered out by Vibe Check`}
          />
          <StatCard
            icon={<CalendarIcon />}
            label="Gaps Filled"
            value={metrics.gap_fills}
            subtext="Cancelled slots recovered from waitlist"
            accent
          />
        </div>

        {/* Charts & Details Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <VibeCheckBar
            approved={metrics.leads_approved}
            filtered={metrics.leads_filtered}
          />
          <ActivityFeed />
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-xs text-brand-charcoal/30">
            Beauty OS — Your AI studio manager, working 24/7 so you don't have to.
          </p>
        </div>
      </main>
    </div>
  )
}
