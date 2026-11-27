import { useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Highlighter, Info } from 'lucide-react'
import type { HighlightToken } from '../types'
import {
  DEFAULT_COLLAPSE_WORD_LIMIT,
  countWords,
  getWeightTier,
  normalizeHighlights,
  segmentHighlightedText,
  truncateToWordLimit,
  type WeightTier,
} from '../utils/highlightText'

export interface HighlightedArticleViewProps {
  text?: string
  highlights?: HighlightToken[]
  verdict: 'REAL' | 'FAKE'
}

const MARK_TIER_CLASSES: Record<'REAL' | 'FAKE', Record<WeightTier, string>> = {
  FAKE: {
    high: 'bg-rose-200/90 text-rose-950 border-b-2 border-rose-500',
    medium: 'bg-rose-100/90 text-rose-900 border-b border-rose-400',
    low: 'bg-amber-100/80 text-amber-950 border-b border-amber-300',
  },
  REAL: {
    high: 'bg-emerald-200/90 text-emerald-950 border-b-2 border-emerald-500',
    medium: 'bg-emerald-100/90 text-emerald-900 border-b border-emerald-400',
    low: 'bg-sky-100/80 text-sky-950 border-b border-sky-300',
  },
}

const CHIP_ACCENT_CLASSES: Record<'REAL' | 'FAKE', { badge: string; bar: string }> = {
  FAKE: {
    badge: 'bg-rose-50/80 text-rose-900 border-rose-200',
    bar: 'bg-rose-500',
  },
  REAL: {
    badge: 'bg-emerald-50/80 text-emerald-900 border-emerald-200',
    bar: 'bg-emerald-500',
  },
}

export function HighlightedArticleView({
  text,
  highlights,
  verdict,
}: HighlightedArticleViewProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const articleText = text?.trim() ?? ''
  const sortedHighlights = useMemo(() => normalizeHighlights(highlights), [highlights])
  const totalWords = useMemo(() => countWords(articleText), [articleText])
  const isLongArticle = totalWords > DEFAULT_COLLAPSE_WORD_LIMIT

  const displayInfo = useMemo(() => {
    if (!isLongArticle || isExpanded) {
      return { text: articleText, isTruncated: false, totalWords }
    }
    return truncateToWordLimit(articleText, DEFAULT_COLLAPSE_WORD_LIMIT)
  }, [articleText, isLongArticle, isExpanded, totalWords])

  const segments = useMemo(
    () => segmentHighlightedText(displayInfo.text, sortedHighlights),
    [displayInfo.text, sortedHighlights]
  )

  if (!articleText) {
    return null
  }

  const chipAccent = CHIP_ACCENT_CLASSES[verdict]
  const hasHighlights = sortedHighlights.length > 0

  return (
    <section
      aria-label="Explainable word highlighting view"
      className="w-full max-w-3xl bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden"
    >
      {/* Top Contributing Words Summary */}
      <div className="p-5 sm:px-6 sm:py-5 border-b border-slate-100">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <Highlighter className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {verdict === 'FAKE'
                ? 'Top Sensationalist / Fake-Leaning Signals'
                : 'Top Credibility / Real-Leaning Signals'}
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-medium tabular-nums">
            {totalWords} words
          </span>
        </div>

        {hasHighlights ? (
          <ul
            aria-label="Top contributing words"
            className="flex flex-wrap items-center gap-2"
          >
            {sortedHighlights.map((token) => {
              const pct = Math.round(token.weight * 100)
              return (
                <li
                  key={token.word.toLowerCase()}
                  title={`Contribution weight: ${pct}%`}
                  className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-medium ${chipAccent.badge}`}
                >
                  <span>{token.word}</span>
                  <span
                    className="w-10 h-1.5 bg-white/80 rounded-full overflow-hidden border border-black/5"
                    aria-hidden="true"
                  >
                    <span
                      className={`block h-full rounded-full ${chipAccent.bar}`}
                      style={{ width: `${pct}%` }}
                    />
                  </span>
                  <span className="text-[11px] font-semibold tabular-nums opacity-80">
                    {pct}%
                  </span>
                </li>
              )
            })}
          </ul>
        ) : (
          <div className="flex items-start gap-2 rounded-xl bg-slate-50 border border-slate-200/70 px-3.5 py-2.5 text-xs text-slate-600">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" aria-hidden="true" />
            <p>
              No specific word-level highlights were returned for this article. Displaying the
              clean article text below.
            </p>
          </div>
        )}
      </div>

      {/* Inline Highlighted Article Body */}
      <div className="p-5 sm:px-6 sm:py-5">
        <div className="text-sm sm:text-[15px] text-slate-800 leading-relaxed whitespace-pre-wrap break-words">
          {segments.map((segment, index) => {
            if (!segment.highlight) {
              return <span key={index}>{segment.text}</span>
            }

            const tier = getWeightTier(segment.highlight.weight)
            const pct = Math.round(segment.highlight.weight * 100)
            const markClasses = MARK_TIER_CLASSES[verdict][tier]

            return (
              <mark
                key={index}
                tabIndex={0}
                title={`Contribution weight: ${pct}%`}
                aria-label={`${segment.text} (contribution weight ${pct}%)`}
                className={`relative group inline rounded-xs px-1 py-0.5 font-medium cursor-help focus:outline-hidden focus:ring-2 focus:ring-blue-400 ${markClasses}`}
              >
                {segment.text}
                <span
                  role="tooltip"
                  className="pointer-events-none opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 z-20 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-[11px] font-medium text-white shadow-md"
                >
                  Weight: {pct}%
                </span>
              </mark>
            )
          })}
        </div>

        {/* Collapsible Long-Text Toggle */}
        {isLongArticle && (
          <div className="mt-4 pt-3 border-t border-slate-100 flex justify-center">
            <button
              type="button"
              onClick={() => setIsExpanded((prev) => !prev)}
              aria-expanded={isExpanded}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200/80 transition-colors cursor-pointer"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4" aria-hidden="true" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" aria-hidden="true" />
                  Expand Full Article ({totalWords} words)
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}

export default HighlightedArticleView
