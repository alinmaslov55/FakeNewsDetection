import { useState } from 'react'
import { ShieldCheck, Sparkles } from 'lucide-react'
import { HighlightedArticleView } from './components/HighlightedArticleView'
import { NewsInputForm } from './components/NewsInputForm'
import { PredictionResultCard } from './components/PredictionResultCard'
import type { HighlightToken, PredictionRequest, PredictionResponse } from './types'

interface PreviewPredictionState {
  result: PredictionResponse
  sourceUrl?: string
}

const SENSATIONAL_CUES =
  /\b(shocking|miracle|elites|leaked video|big pharma|deleted|secret)\b|!{2,}/i

const PREVIEW_FAKE_TERMS: HighlightToken[] = [
  { word: 'shocking', weight: 1.0 },
  { word: 'miracle', weight: 0.86 },
  { word: 'big pharma', weight: 0.74 },
  { word: 'leaked video', weight: 0.62 },
  { word: 'elites', weight: 0.51 },
  { word: 'deleted', weight: 0.36 },
  { word: 'secret', weight: 0.28 },
]

const PREVIEW_REAL_TERMS: HighlightToken[] = [
  { word: 'International Energy Agency', weight: 1.0 },
  { word: 'reported', weight: 0.78 },
  { word: 'renewable energy', weight: 0.64 },
  { word: 'manufacturing', weight: 0.45 },
  { word: 'markets', weight: 0.31 },
]

function extractPreviewHighlights(
  text: string,
  candidates: HighlightToken[]
): HighlightToken[] {
  const lower = text.toLowerCase()
  return candidates.filter((item) => lower.includes(item.word.toLowerCase()))
}

function buildSimulatedPrediction(
  payload: PredictionRequest
): PreviewPredictionState {
  if (payload.url) {
    const simulatedText =
      'The central bank reported on Thursday that benchmark interest rates remain unchanged following quarterly inflation data released by the national statistics bureau.'
    return {
      sourceUrl: payload.url,
      result: {
        verdict: 'REAL',
        confidence: 0.912,
        title: 'Extracted News Article Headline (Preview)',
        text: simulatedText,
        highlights: [
          { word: 'central bank', weight: 1.0 },
          { word: 'reported', weight: 0.76 },
          { word: 'inflation', weight: 0.54 },
          { word: 'statistics', weight: 0.34 },
        ],
      },
    }
  }

  const text = payload.text ?? ''
  const isLikelyFake = SENSATIONAL_CUES.test(text)
  const highlights = extractPreviewHighlights(
    text,
    isLikelyFake ? PREVIEW_FAKE_TERMS : PREVIEW_REAL_TERMS
  )

  return {
    result: {
      verdict: isLikelyFake ? 'FAKE' : 'REAL',
      confidence: isLikelyFake ? 0.946 : 0.894,
      text,
      highlights,
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
              WEB-03 Ready
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

        {/* Credibility Verdict, Confidence Score & Word Highlighting */}
        {prediction && (
          <div className="w-full flex flex-col items-center gap-6 mt-6">
            <PredictionResultCard
              result={prediction.result}
              sourceUrl={prediction.sourceUrl}
            />
            <HighlightedArticleView
              text={prediction.result.text}
              highlights={prediction.result.highlights}
              verdict={prediction.result.verdict}
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
