/**
 * Type definitions for Fake News Detection System API
 */

export interface HighlightToken {
  word: string
  weight: number
}

export interface PredictionResponse {
  verdict: 'REAL' | 'FAKE'
  confidence: number
  title?: string
  text?: string
  highlights?: HighlightToken[]
}

export interface PredictionRequest {
  text?: string
  url?: string
}

export interface FeedbackRequest {
  predictedVerdict: 'REAL' | 'FAKE'
  userFeedback: 'AGREE' | 'DISAGREE'
  comment?: string
}

