import {
  ExternalLink,
  Info,
  Newspaper,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import type { PredictionResponse } from '../types'
import {
  formatConfidencePercentage,
  getConfidenceTier,
  toConfidencePercentage,
  type ConfidenceTierLevel,
} from '../utils/confidence'

export interface PredictionResultCardProps {
  result: PredictionResponse
  sourceUrl?: string
}

const VERDICT_CONFIG = {
  REAL: {
    badgeLabel: 'REAL',
    headline: 'Likely Credible',
    summary: 'Linguistic patterns align with standard factual reporting.',
    Icon: ShieldCheck,
    bannerClasses: 'bg-emerald-50/80 border-emerald-200 text-emerald-950',
    iconWrapClasses: 'bg-emerald-600 text-white shadow-xs',
    badgeClasses: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    progressClasses: 'bg-emerald-500',
  },
  FAKE: {
    badgeLabel: 'FAKE',
    headline: 'Likely Fabricated / Unreliable',
    summary: 'Linguistic patterns resemble sensationalist or misleading content.',
    Icon: ShieldAlert,
    bannerClasses: 'bg-rose-50/80 border-rose-200 text-rose-950',
    iconWrapClasses: 'bg-rose-600 text-white shadow-xs',
    badgeClasses: 'bg-rose-100 text-rose-800 border-rose-300',
    progressClasses: 'bg-rose-500',
  },
} as const

const CERTAINTY_BADGE_CLASSES: Record<ConfidenceTierLevel, string> = {
  low: 'bg-amber-50 text-amber-800 border-amber-200',
  moderate: 'bg-blue-50 text-blue-800 border-blue-200',
  high: 'bg-slate-100 text-slate-800 border-slate-200',
}

function getSafeExternalUrl(rawUrl?: string): string | null {
  const trimmed = rawUrl?.trim()
  if (!trimmed) {
    return null
  }
  return /^https?:\/\//i.test(trimmed) ? trimmed : null
}

export function PredictionResultCard({
  result,
  sourceUrl,
}: PredictionResultCardProps) {
  const percentage = toConfidencePercentage(result.confidence)
  const formattedPercentage = formatConfidencePercentage(result.confidence)
  const certainty = getConfidenceTier(percentage)
  const config = VERDICT_CONFIG[result.verdict]
  const VerdictIcon = config.Icon

  const extractedTitle = result.title?.trim()
  const safeSourceUrl = getSafeExternalUrl(sourceUrl)
  const hasScrapedMetadata = Boolean(extractedTitle || safeSourceUrl)

  return (
    <section
      aria-label="Credibility prediction result"
      className="w-full max-w-3xl bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden"
    >
      {/* Verdict Banner */}
      <div
        className={`p-5 sm:p-6 border-b flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 ${config.bannerClasses}`}
      >
        <div className="flex items-start sm:items-center gap-3.5">
          <div className={`p-3 rounded-xl shrink-0 ${config.iconWrapClasses}`}>
            <VerdictIcon className="w-6 h-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wider uppercase border ${config.badgeClasses}`}
              >
                {config.badgeLabel}
              </span>
              <h2 className="text-lg sm:text-xl font-bold tracking-tight">
                {config.headline}
              </h2>
            </div>
            <p className="text-sm opacity-85 mt-1">{config.summary}</p>
          </div>
        </div>

        <div className="sm:text-right shrink-0">
          <span className="text-xs font-semibold uppercase tracking-wider opacity-75 block">
            Confidence
          </span>
          <span className="text-2xl sm:text-3xl font-extrabold tabular-nums">
            {formattedPercentage}
          </span>
        </div>
      </div>

      {/* Confidence Score Meter */}
      <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Certainty Assessment
          </span>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${CERTAINTY_BADGE_CLASSES[certainty.level]}`}
          >
            {certainty.label}
          </span>
        </div>

        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200/70">
          <div
            role="progressbar"
            aria-label="Model confidence score"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percentage}
            style={{ width: `${percentage}%` }}
            className={`h-full rounded-full transition-all duration-500 ease-out ${config.progressClasses}`}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
          <span>0%</span>
          <span>50% (Borderline)</span>
          <span>100%</span>
        </div>
      </div>

      {/* Scraped Metadata Header (shown when analyzed via URL or title is present) */}
      {hasScrapedMetadata && (
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 bg-slate-50/40 flex items-start gap-3">
          <Newspaper
            className="w-4 h-4 text-slate-400 shrink-0 mt-1"
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1 space-y-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">
              Analyzed Article Source
            </span>
            {extractedTitle && (
              <h3 className="text-sm sm:text-base font-semibold text-slate-900 leading-snug">
                {extractedTitle}
              </h3>
            )}
            {safeSourceUrl && (
              <a
                href={safeSourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 hover:underline break-all"
              >
                <span>{safeSourceUrl}</span>
                <ExternalLink className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
              </a>
            )}
          </div>
        </div>
      )}

      {/* AI Disclaimer Subtitle */}
      <div className="px-5 sm:px-6 py-3 bg-slate-50/70 flex items-start gap-2 text-xs text-slate-600">
        <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" aria-hidden="true" />
        <p>
          This score reflects automated NLP linguistic pattern analysis rather than
          factual verification of live events.
        </p>
      </div>
    </section>
  )
}

export default PredictionResultCard
