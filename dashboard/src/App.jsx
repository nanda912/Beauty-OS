import React, { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'

const OnboardingWizard = lazy(() => import('./pages/OnboardingWizard'))
const Dashboard = lazy(() => import('./pages/Dashboard'))

function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-cream">
      <div className="animate-pulse text-brand-gold font-display text-2xl">
        Loading...
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboard/:slug" element={<OnboardingWizard />} />
        <Route path="/dashboard/:slug" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Suspense>
  )
}
