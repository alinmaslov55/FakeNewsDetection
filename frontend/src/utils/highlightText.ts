import type { HighlightToken } from '../types'

export type WeightTier = 'high' | 'medium' | 'low'

export interface TextSegment {
  text: string
  highlight?: HighlightToken
}

export interface TruncatedArticle {
  text: string
  isTruncated: boolean
  totalWords: number
}

export const DEFAULT_COLLAPSE_WORD_LIMIT = 300

/**
 * Clamp a highlight weight into [0, 1], guarding against NaN or non-finite values.
 */
export function normalizeWeight(weight: number): number {
  if (!Number.isFinite(weight)) {
    return 0
  }
  return Math.min(1, Math.max(0, Math.abs(weight)))
}

/**
 * Map a normalized [0, 1] weight to a visual intensity tier.
 */
export function getWeightTier(weight: number): WeightTier {
  const normalized = normalizeWeight(weight)
  if (normalized >= 0.7) {
    return 'high'
  }
  if (normalized >= 0.4) {
    return 'medium'
  }
  return 'low'
}

/**
 * Count whitespace-delimited words in an article string.
 */
export function countWords(text: string): number {
  const trimmed = text.trim()
  if (!trimmed) {
    return 0
  }
  return trimmed.split(/\s+/).length
}

/**
 * Truncate text to at most `wordLimit` words while preserving original formatting.
 */
export function truncateToWordLimit(
  text: string,
  wordLimit: number = DEFAULT_COLLAPSE_WORD_LIMIT
): TruncatedArticle {
  const totalWords = countWords(text)
  if (totalWords <= wordLimit || wordLimit <= 0) {
    return { text, isTruncated: false, totalWords }
  }

  const wordRegex = /\S+/g
  let count = 0
  let cutoffIndex = text.length

  for (const match of text.matchAll(wordRegex)) {
    count += 1
    if (count === wordLimit) {
      cutoffIndex = (match.index ?? 0) + match[0].length
      break
    }
  }

  return {
    text: `${text.slice(0, cutoffIndex).trimEnd()}...`,
    isTruncated: true,
    totalWords,
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Deduplicate highlights (keeping highest normalized weight per term) and sort descending by weight.
 */
export function normalizeHighlights(highlights?: HighlightToken[]): HighlightToken[] {
  if (!highlights || highlights.length === 0) {
    return []
  }

  const bestByTerm = new Map<string, HighlightToken>()

  for (const item of highlights) {
    const trimmedWord = item.word?.trim()
    if (!trimmedWord || !Number.isFinite(item.weight)) {
      continue
    }

    const weight = normalizeWeight(item.weight)
    if (weight <= 0) {
      continue
    }

    const key = trimmedWord.toLowerCase()
    const existing = bestByTerm.get(key)
    if (!existing || weight > existing.weight) {
      bestByTerm.set(key, { word: trimmedWord, weight })
    }
  }

  return Array.from(bestByTerm.values()).sort((a, b) => b.weight - a.weight)
}

/**
 * Split raw article text into plain and highlighted segments without HTML injection.
 * Matches whole words/phrases case-insensitively, preferring longest phrases first.
 */
export function segmentHighlightedText(
  text: string,
  highlights?: HighlightToken[]
): TextSegment[] {
  if (!text) {
    return []
  }

  const normalized = normalizeHighlights(highlights)
  if (normalized.length === 0) {
    return [{ text }]
  }

  // Sort longest phrases first so e.g. "miracle cure" matches before "miracle"
  const byLength = [...normalized].sort((a, b) => b.word.length - a.word.length)
  const lookup = new Map<string, HighlightToken>(
    byLength.map((token) => [token.word.toLowerCase(), token])
  )

  const alternation = byLength.map((token) => escapeRegExp(token.word)).join('|')
  const matcher = new RegExp(`(?<![A-Za-z0-9_])(${alternation})(?![A-Za-z0-9_])`, 'gi')

  const segments: TextSegment[] = []
  let lastIndex = 0

  for (const match of text.matchAll(matcher)) {
    const matchIndex = match.index ?? 0
    const matchedText = match[0]

    if (matchIndex > lastIndex) {
      segments.push({ text: text.slice(lastIndex, matchIndex) })
    }

    const token = lookup.get(matchedText.toLowerCase())
    segments.push(token ? { text: matchedText, highlight: token } : { text: matchedText })
    lastIndex = matchIndex + matchedText.length
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex) })
  }

  return segments.length > 0 ? segments : [{ text }]
}
