import { Newspaper, ShieldCheck } from 'lucide-react'

export function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-600 text-white rounded-lg">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <span className="font-semibold text-lg text-slate-800">
              Fake News Detection System
            </span>
          </div>
          <span className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 font-medium rounded-full border border-blue-200">
            Frontend Initialized
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto px-4 py-16 flex flex-col items-center justify-center text-center">
        <div className="p-4 bg-blue-100 text-blue-600 rounded-full mb-6">
          <Newspaper className="w-10 h-10" />
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mb-4">
          Fake News Detector Frontend
        </h1>
        <p className="text-slate-600 max-w-lg mb-8 leading-relaxed">
          The React + TypeScript + Tailwind CSS client environment is initialized and configured.
          Ready for milestone component implementation and backend integration.
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Environment ready: Vite, React 19, TypeScript, Tailwind CSS
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Fake News Detection System &bull; Frontend Workspace
      </footer>
    </div>
  )
}

export default App
