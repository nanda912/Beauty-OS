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

function UsersIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
    </svg>
  )
}

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

function TrendingUpIcon() {
  return (
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
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

// ── Client Acquisition Funnel ───────────────────────────────────────

function AcquisitionFunnel({ approved, filtered }) {
  const total = approved + filtered
  const approvedPct = total > 0 ? (approved / total) * 100 : 0

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-brand-pink/20">
      <h3 className="text-sm font-medium text-brand-charcoal/60 uppercase tracking-wide mb-4">
        Client Acquisition Funnel
      </h3>
      <div className="flex items-end justify-between mb-3">
        <div>
          <span className="text-2xl font-bold font-display">{approved}</span>
          <span className="text-sm text-brand-charcoal/50 ml-1">acquired</span>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold font-display text-brand-pink-dark">{filtered}</span>
          <span className="text-sm text-brand-charcoal/50 ml-1">filtered out</span>
        </div>
      </div>
      <div className="h-3 bg-brand-pink-light rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-gold to-brand-gold-light rounded-full transition-all duration-700"
          style={{ width: `${approvedPct}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-brand-charcoal/40">
        {total > 0 ? `${approvedPct.toFixed(0)}% acquisition rate` : 'Leads incoming'} — the Gatekeeper is protecting your calendar
      </p>

      {/* Funnel breakdown */}
      <div className="mt-4 pt-4 border-t border-brand-pink/10 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-charcoal/20" />
            <span className="text-brand-charcoal/60">Leads found by Hunter</span>
          </div>
          <span className="font-medium text-brand-charcoal">{total}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-pink-dark" />
            <span className="text-brand-charcoal/60">Filtered by Gatekeeper</span>
          </div>
          <span className="font-medium text-brand-charcoal">{filtered}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-gold" />
            <span className="text-brand-charcoal/60">Booked & deposited</span>
          </div>
          <span className="font-medium text-brand-charcoal">{approved}</span>
        </div>
      </div>
    </div>
  )
}

// ── Growth Feed ─────────────────────────────────────────────────────

function GrowthFeed({ metrics }) {
  const activities = [
    { time: 'Active', text: 'Social Hunter scanning for local leads', type: 'hunter', icon: '🎯' },
    { time: 'Active', text: 'Gatekeeper screening inbound DMs', type: 'gatekeeper', icon: '🛡️' },
    { time: 'Active', text: 'Revenue Engine queuing upsell texts', type: 'revenue', icon: '💰' },
  ]

  // Add dynamic entries based on real metrics
  if (metrics.leads_approved > 0) {
    activities.push({ time: 'Recent', text: `${metrics.leads_approved} new clients acquired by AI`, type: 'revenue', icon: '✅' })
  }
  if (metrics.found_money > 0) {
    activities.push({ time: 'Recent', text: `$${metrics.found_money} in found money from upsells`, type: 'revenue', icon: '💵' })
  }
  if (metrics.gap_fills > 0) {
    activities.push({ time: 'Recent', text: `${metrics.gap_fills} cancelled slots recovered`, type: 'gatekeeper', icon: '📅' })
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-brand-pink/20">
      <h3 className="text-sm font-medium text-brand-charcoal/60 uppercase tracking-wide mb-4">
        AI Growth Activity
      </h3>
      <div className="space-y-3">
        {activities.map((a, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-base flex-shrink-0">{a.icon}</span>
            <span className="text-sm text-brand-charcoal/80 flex-1">{a.text}</span>
            <span className={`text-xs flex-shrink-0 px-2 py-0.5 rounded-full font-medium ${
              a.time === 'Active'
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-brand-gold/10 text-brand-gold-dark'
            }`}>
              {a.time}
            </span>
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
              {slug ? slug.replace(/-/g, ' ') : 'Growth Dashboard'}
            </p>
          </Link>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              AI Hunting for Clients
            </span>
          </div>
        </div>
      </header>

      {/* Dashboard Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <StatCard
            icon={<UsersIcon />}
            label="New Clients Acquired"
            value={metrics.leads_approved}
            subtext="Found, screened, and booked by AI"
            accent
          />
          <StatCard
            icon={<DollarIcon />}
            label="Total Found Money"
            value={`$${metrics.found_money.toLocaleString()}`}
            subtext="Upsell revenue you didn't have to sell"
            accent
          />
          <StatCard
            icon={<ClockIcon />}
            label="Hours Reclaimed"
            value={`${metrics.hours_reclaimed}h`}
            subtext={`${metrics.ai_chats} conversations handled by AI`}
          />
          <StatCard
            icon={<TrendingUpIcon />}
            label="Growth Actions"
            value={metrics.leads_approved + metrics.leads_filtered + metrics.gap_fills}
            subtext={`${metrics.gap_fills} cancelled slots recovered`}
          />
        </div>

        {/* Charts & Details Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <AcquisitionFunnel
            approved={metrics.leads_approved}
            filtered={metrics.leads_filtered}
          />
          <GrowthFeed metrics={metrics} />
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-xs text-brand-charcoal/30">
            Beauty OS — Finding, screening, and booking your clients 24/7 so you can focus on your craft.
          </p>
        </div>
      </main>
    </div>
  )
}
