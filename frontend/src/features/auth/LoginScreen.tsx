import type { ReactNode } from 'react'
import { Bot, Database, LogIn, ShieldCheck, Sparkles } from 'lucide-react'

type Props = { error: string; googleUrl: string; developmentEnabled: boolean; onDevelopmentLogin: () => void }

export function LoginScreen({ error, googleUrl, developmentEnabled, onDevelopmentLogin }: Props) {
  return <main className="grid min-h-screen bg-[#f6f7f1] text-stone-900 lg:grid-cols-[1.05fr_.95fr]">
    <section className="relative hidden overflow-hidden bg-[#0d3028] p-14 text-white lg:flex lg:flex-col">
      <div className="absolute -right-32 -top-32 size-96 rounded-full bg-lime-300/10 blur-3xl" />
      <div className="relative flex items-center gap-4"><div className="grid size-14 place-items-center rounded-2xl border border-emerald-300/30 text-2xl font-bold text-lime-300">S</div><div><h1 className="text-3xl font-bold">Sentinel</h1><p className="text-xs tracking-[.2em] text-emerald-200">CIS INTELLIGENCE</p></div></div>
      <div className="relative my-auto max-w-xl"><p className="text-sm font-bold tracking-[.2em] text-lime-300">PRIVATE SECURITY KNOWLEDGE</p><h2 className="mt-5 text-5xl font-bold leading-tight">Ask the controls.<br /><span className="text-lime-300">Trust the evidence.</span></h2><p className="mt-6 max-w-lg text-lg leading-8 text-emerald-100">Explore CIS Controls v8 with locally generated answers, page-level citations, persistent investigations, and structured feedback.</p><div className="mt-10 grid gap-4 sm:grid-cols-3"><Feature icon={<Sparkles size={19} />} text="Grounded answers" /><Feature icon={<Database size={19} />} text="Saved threads" /><Feature icon={<ShieldCheck size={19} />} text="Local by design" /></div></div>
      <p className="relative text-sm text-emerald-200">React · .NET · FastAPI · Weaviate · Ollama · MongoDB</p>
    </section>
    <section className="flex items-center justify-center p-6 sm:p-12"><div className="w-full max-w-md"><div className="mb-10 flex items-center gap-3 lg:hidden"><div className="grid size-12 place-items-center rounded-2xl bg-[#0d3028] text-xl font-bold text-lime-300">S</div><div><p className="text-2xl font-bold">Sentinel</p><p className="text-xs tracking-[.16em] text-emerald-700">CIS INTELLIGENCE</p></div></div><div className="rounded-[2rem] border border-stone-200 bg-white p-8 shadow-2xl shadow-stone-900/5 sm:p-10"><div className="grid size-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-800"><Bot size={23} /></div><h2 className="mt-6 text-3xl font-bold">Welcome back</h2><p className="mt-3 leading-7 text-stone-600">Sign in to access your private knowledge workspace and resume saved conversations.</p>{error && <div role="alert" className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{error}</div>}<div className="mt-8 space-y-3"><a href={googleUrl} className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-5 py-3.5 font-semibold text-white transition hover:bg-emerald-800"><LogIn size={18} />Sign in with Google</a>{developmentEnabled && <button type="button" onClick={onDevelopmentLogin} className="w-full rounded-xl border border-stone-300 bg-white px-5 py-3.5 font-semibold transition hover:border-emerald-400 hover:bg-emerald-50">Continue with local demo</button>}</div><p className="mt-7 text-center text-xs leading-5 text-stone-400">Models and documents remain on this machine. Local demo access is available only in Development mode.</p></div></div></section>
  </main>
}

function Feature({ icon, text }: { icon: ReactNode; text: string }) {
  return <div className="rounded-2xl border border-emerald-300/15 bg-white/5 p-4"><span className="text-lime-300">{icon}</span><p className="mt-3 text-sm font-semibold text-emerald-50">{text}</p></div>
}
