export type ConfidenceTierLevel = 'low' | 'moderate' | 'high'

export interface ConfidenceTierInfo {
  level: ConfidenceTierLevel
  label: string
}

/**
 * Clamp raw confidence into [0, 1], guarding against NaN or non-finite inputs.
 */
export function normalizeConfidence(confidence: number): number {
  if (!Number.isFinite(confidence)) {
    return 0
  }
  return Math.min(1, Math.max(0, confidence))
}

/**
 * Convert a [0, 1] confidence score into a [0, 100] percentage rounded to 1 decimal place.
 */
export function toConfidencePercentage(confidence: number): number {
  const normalized = normalizeConfidence(confidence)
  return Math.round(normalized * 1000) / 10
}

/**
 * Format a [0, 1] confidence score as a percentage label (e.g., "93.4%").
 */
export function formatConfidencePercentage(confidence: number): string {
  return `${toConfidencePercentage(confidence).toFixed(1)}%`
}

/**
 * Map a [0, 100] confidence percentage to its semantic certainty tier.
 */
export function getConfidenceTier(percentage: number): ConfidenceTierInfo {
  if (percentage >= 85) {
    return { level: 'high', label: 'High Confidence' }
  }
  if (percentage >= 65) {
    return { level: 'moderate', label: 'Moderate Confidence' }
  }
  return { level: 'low', label: 'Low Confidence (Borderline)' }
}
