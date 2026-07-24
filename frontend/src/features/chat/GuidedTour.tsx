import { useEffect, useState } from 'react'

const steps = [
  { title: 'Your persistent workspace', text: 'Every authenticated conversation is saved in MongoDB and appears in the thread list.' },
  { title: 'Grounded citations', text: 'Click a green citation to inspect its source page and evidence snippet.' },
  { title: 'Improve every answer', text: 'Regenerate responses, switch versions, and rate each version with structured feedback.' },
]

export function GuidedTour() {
  const [step, setStep] = useState(-1)
  useEffect(() => { if (!localStorage.getItem('sentinel-tour-complete')) setStep(0) }, [])
  if (step < 0) return null

  const finish = () => {
    localStorage.setItem('sentinel-tour-complete', 'true')
    setStep(-1)
  }

  return <div className="fixed inset-0 z-[70] grid place-items-center bg-stone-950/55 p-5 backdrop-blur-sm">
    <section role="dialog" aria-modal="true" aria-labelledby="tour-title" className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl">
      <p className="text-xs font-bold tracking-[.18em] text-emerald-700">QUICK TOUR · {step + 1}/{steps.length}</p>
      <h2 id="tour-title" className="mt-3 text-2xl font-bold">{steps[step].title}</h2>
      <p className="mt-3 leading-7 text-stone-600">{steps[step].text}</p>
      <div className="mt-7 flex justify-between">
        <button type="button" onClick={finish} className="text-sm font-semibold text-stone-500">Skip tour</button>
        <button type="button" autoFocus onClick={() => step === steps.length - 1 ? finish() : setStep(step + 1)} className="rounded-xl bg-emerald-700 px-5 py-3 font-semibold text-white">{step === steps.length - 1 ? 'Start exploring' : 'Next'}</button>
      </div>
    </section>
  </div>
}
