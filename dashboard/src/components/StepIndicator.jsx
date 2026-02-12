import React from 'react'

const STEPS = [
  { num: 1, label: 'Services' },
  { num: 2, label: 'Add-Ons' },
  { num: 3, label: 'Policies' },
  { num: 4, label: 'Voice' },
  { num: 5, label: 'Demo' },
]

export default function StepIndicator({ current }) {
  return (
    <div className="flex items-center justify-center gap-1 mb-8">
      {STEPS.map((step, i) => (
        <React.Fragment key={step.num}>
          <div className="flex flex-col items-center">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                step.num < current
                  ? 'bg-brand-gold text-white'
                  : step.num === current
                  ? 'bg-brand-charcoal text-white ring-4 ring-brand-gold/20'
                  : 'bg-brand-pink-light text-brand-charcoal/40'
              }`}
            >
              {step.num < current ? '✓' : step.num}
            </div>
            <span className={`text-xs mt-1 ${
              step.num === current ? 'text-brand-charcoal font-medium' : 'text-brand-charcoal/40'
            }`}>
              {step.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-8 h-0.5 mb-4 ${
              step.num < current ? 'bg-brand-gold' : 'bg-brand-pink/30'
            }`} />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}
