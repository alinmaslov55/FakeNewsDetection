import { useState } from 'react'
import { ShieldCheck, Sparkles, CheckCircle2, Globe, FileText } from 'lucide-react'
import { NewsInputForm } from './components/NewsInputForm'
import type { PredictionRequest } from './types'

export function App() {
  const [lastSubmission, setLastSubmission] = useState<PredictionRequest | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (payload: PredictionRequest) => {
    setIsLoading(true)
    // Simulate API delay for Milestone 2 testing until INT-01 backend wiring
    await new Promise((resolve) => setTimeout(resolve, 800))
    setLastSubmission(payload)
    setIsLoading(false)
  }

  const handleClear = () => {
    setLastSubmission(null)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Navigation Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-600 text-white rounded-xl shadow-xs">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base text-slate-900 tracking-tight block">
                Fake News Detector
              </span>
              <span className="text-[11px] text-slate-500 block -mt-0.5">
                NLP & Machine Learning Credibility System
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2.5 py-1 bg-emerald-50 text-emerald-700 font-medium rounded-full border border-emerald-200 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              WEB-01 Ready
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-10 sm:py-14 flex flex-col items-center">
        {/* Hero Section */}
        <div className="text-center max-w-xl mx-auto mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold mb-3 border border-blue-200/60">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            Milestone 2 &bull; Article Input Interface
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mb-3">
            Verify News Credibility
          </h1>
          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            Submit a live news article URL or paste paragraph text to evaluate linguistic credibility,
            detect sensationalist patterns, and analyze source integrity.
          </p>
        </div>

        {/* News Input Component */}
        <NewsInputForm
          onSubmit={handleSubmit}
          onClear={handleClear}
          isLoading={isLoading}
        />

        {/* Interactive Submission Preview (Milestone 2 Test View) */}
        {lastSubmission && (
          <div className="w-full max-w-3xl mt-6 p-5 bg-white border border-slate-200 rounded-2xl shadow-xs animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Submitted Request Payload
              </span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono">
                Ready for Backend API
              </span>
            </div>

            {lastSubmission.url ? (
              <div className="space-y-1">
                <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-blue-600" />
                  URL Target:
                </span>
                <p className="text-sm font-mono text-blue-600 break-all bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  {lastSubmission.url}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5 text-blue-600" />
                  Text Payload ({lastSubmission.text?.length} characters):
                </span>
                <p className="text-xs font-mono text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100 max-h-36 overflow-y-auto whitespace-pre-wrap">
                  {lastSubmission.text}
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        Fake News Detection System &bull; Frontend Client
      </footer>
    </div>
  )
}

export default App
