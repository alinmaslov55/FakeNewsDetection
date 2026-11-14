import { useState } from 'react'
import { ShieldCheck, Sparkles } from 'lucide-react'
import { NewsInputForm } from './components/NewsInputForm'
import { PredictionResultCard } from './components/PredictionResultCard'
import type { PredictionRequest, PredictionResponse } from './types'

interface PreviewPredictionState {
  result: PredictionResponse
  sourceUrl?: string
}

const SENSATIONAL_CUES =
  /\b(shocking|miracle|elites|leaked video|big pharma|deleted|secret)\b|!{2,}/i

function buildSimulatedPrediction(
  payload: PredictionRequest
): PreviewPredictionState {
  if (payload.url) {
    return {
      sourceUrl: payload.url,
      result: {
        verdict: 'REAL',
        confidence: 0.912,
        title: 'Extracted News Article Headline (Preview)',
        text: 'Simulated article body extracted from the submitted URL for WEB-02 preview.',
        highlights: [],
      },
    }
  }

  const text = payload.text ?? ''
  const isLikelyFake = SENSATIONAL_CUES.test(text)

  return {
    result: {
      verdict: isLikelyFake ? 'FAKE' : 'REAL',
      confidence: isLikelyFake ? 0.946 : 0.894,
      text,
      highlights: [],
    },
  }
}

export function App() {
  const [prediction, setPrediction] = useState<PreviewPredictionState | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (payload: PredictionRequest) => {
    setIsLoading(true)
    // Simulate API delay until INT-01 wires live FastAPI endpoints
    await new Promise((resolve) => setTimeout(resolve, 600))
    setPrediction(buildSimulatedPrediction(payload))
    setIsLoading(false)
  }

  const handleClear = () => {
    setPrediction(null)
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
              WEB-02 Ready
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
            Credibility Verdict & Confidence Scoring
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mb-3">
            Verify News Credibility
          </h1>
          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            Submit a live news article URL or paste paragraph text to evaluate linguistic credibility,
            detect sensationalist patterns, and inspect model confidence.
          </p>
        </div>

        {/* News Input Component */}
        <NewsInputForm
          onSubmit={handleSubmit}
          onClear={handleClear}
          isLoading={isLoading}
        />

        {/* Credibility Verdict & Confidence Score Card */}
        {prediction && (
          <div className="w-full flex justify-center mt-6">
            <PredictionResultCard
              result={prediction.result}
              sourceUrl={prediction.sourceUrl}
            />
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
