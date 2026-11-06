import { useState } from 'react'
import {
  Link2,
  FileText,
  Search,
  Loader2,
  RotateCcw,
  AlertCircle,
  Sparkles,
} from 'lucide-react'
import type { PredictionRequest } from '../types'
import { SAMPLE_ARTICLES } from '../data/samples'

export interface NewsInputFormProps {
  onSubmit: (payload: PredictionRequest) => void | Promise<void>
  onClear?: () => void
  isLoading?: boolean
  disabled?: boolean
}

export function NewsInputForm({
  onSubmit,
  onClear,
  isLoading = false,
  disabled = false,
}: NewsInputFormProps) {
  const [mode, setMode] = useState<'url' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [urlError, setUrlError] = useState<string | null>(null)

  const isControlsDisabled = disabled || isLoading
  const trimmedText = text.trim()
  const charCount = trimmedText.length
  const wordCount = trimmedText ? trimmedText.split(/\s+/).filter(Boolean).length : 0
  const isTextValid = charCount >= 30

  // URL Validation helper
  const validateUrl = (value: string): boolean => {
    const trimmed = value.trim()
    if (!trimmed) {
      setUrlError('Please enter a news article URL.')
      return false
    }

    try {
      const parsed = new URL(trimmed)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        setUrlError('URL must begin with http:// or https://')
        return false
      }
      setUrlError(null)
      return true
    } catch {
      setUrlError('Please enter a valid web URL (e.g. https://example.com/article)')
      return false
    }
  }

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(e.target.value)
    if (urlError) {
      // Clear error as user types if it becomes valid or empty
      if (!e.target.value.trim()) {
        setUrlError(null)
      } else {
        try {
          const parsed = new URL(e.target.value.trim())
          if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
            setUrlError(null)
          }
        } catch {
          // Keep typing
        }
      }
    }
  }

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if (isControlsDisabled) return

    if (mode === 'url') {
      if (!validateUrl(url)) return
      onSubmit({ url: url.trim() })
    } else {
      if (!isTextValid) return
      onSubmit({ text: trimmedText })
    }
  }

  const handleClear = () => {
    if (isControlsDisabled) return
    setUrl('')
    setText('')
    setUrlError(null)
    onClear?.()
  }

  const handleLoadSample = (sampleId: string) => {
    if (isControlsDisabled) return
    const sample = SAMPLE_ARTICLES.find((s) => s.id === sampleId)
    if (!sample) return

    if (sample.type === 'url') {
      setMode('url')
      setUrl(sample.content)
      setUrlError(null)
    } else {
      setMode('text')
      setText(sample.content)
    }
  }

  const handleKeyDownTextarea = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (isTextValid && !isControlsDisabled) {
        handleSubmit()
      }
    }
  }

  // Determine if submit is permitted
  const isSubmitDisabled =
    isControlsDisabled ||
    (mode === 'url' ? !url.trim() : !isTextValid)

  return (
    <div className="w-full max-w-3xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-7 transition-all">
      {/* Mode Selector Tabs */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200/80">
          <button
            type="button"
            onClick={() => {
              setMode('url')
              setUrlError(null)
            }}
            disabled={isControlsDisabled}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === 'url'
                ? 'bg-white text-blue-600 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Link2 className="w-4 h-4" />
            Paste URL
          </button>
          <button
            type="button"
            onClick={() => setMode('text')}
            disabled={isControlsDisabled}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode === 'text'
                ? 'bg-white text-blue-600 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-4 h-4" />
            Paste Article Text
          </button>
        </div>

        {/* Live counter badge for Text Mode */}
        {mode === 'text' && (
          <div className="flex items-center gap-2 text-xs font-medium">
            <span className="text-slate-500">{wordCount} words</span>
            <span
              className={`px-2 py-0.5 rounded-full border transition-colors ${
                isTextValid
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              {charCount} / 30 min chars
            </span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} noValidate>
        {/* Mode 1: URL Input */}
        {mode === 'url' ? (
          <div className="space-y-2 mb-4">
            <label
              htmlFor="news-url-input"
              className="block text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              News Article Link
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Link2 className="w-4 h-4" />
              </div>
              <input
                id="news-url-input"
                type="url"
                value={url}
                onChange={handleUrlChange}
                onBlur={() => url.trim() && validateUrl(url)}
                disabled={isControlsDisabled}
                placeholder="https://www.bbc.com/news/article-headline"
                className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 transition-all ${
                  urlError
                    ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-100 bg-rose-50/20'
                    : 'border-slate-200 focus:border-blue-500 focus:ring-blue-100 bg-slate-50/50 focus:bg-white'
                }`}
              />
            </div>
            {urlError && (
              <p className="flex items-center gap-1.5 text-xs text-rose-600 mt-1.5 font-medium">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {urlError}
              </p>
            )}
          </div>
        ) : (
          /* Mode 2: Textarea Input */
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between">
              <label
                htmlFor="news-text-input"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Article Content
              </label>
              <span className="text-[11px] text-slate-400">Press Ctrl+Enter to submit</span>
            </div>
            <textarea
              id="news-text-input"
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDownTextarea}
              disabled={isControlsDisabled}
              placeholder="Paste headline and article paragraphs here to analyze credibility..."
              className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-slate-50/50 focus:bg-white transition-all resize-y min-h-[140px]"
            />
            {charCount > 0 && !isTextValid && (
              <p className="flex items-center gap-1.5 text-xs text-amber-600 mt-1 font-medium">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                Please enter at least 30 characters ({30 - charCount} more needed)
              </p>
            )}
          </div>
        )}

        {/* Quick Sample Presets */}
        <div className="pt-2 pb-4 border-t border-slate-100 flex items-center flex-wrap gap-2">
          <span className="text-xs font-medium text-slate-500 inline-flex items-center gap-1 mr-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Try sample:
          </span>
          {SAMPLE_ARTICLES.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => handleLoadSample(sample.id)}
              disabled={isControlsDisabled}
              title={sample.description}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200/60 hover:border-blue-200 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sample.label}
            </button>
          ))}
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
          <button
            type="button"
            onClick={handleClear}
            disabled={isControlsDisabled || (!url && !text)}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <RotateCcw className="w-4 h-4" />
            Clear
          </button>

          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing news...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Check News
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
