import { useState, useEffect, useRef, useCallback } from 'react'
import { categories } from '../soundbites.js'

export default function Player({ bite, onNext, onPrev, onRandom, totalCount, currentIndex }) {
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const [available, setAvailable] = useState(true)
  const [copied, setCopied] = useState(false)
  const audioRef = useRef(null)

  const copyLink = useCallback(() => {
    const url = `${window.location.origin}${window.location.pathname}#${bite.id}`
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [bite.id])

  useEffect(() => {
    setPlaying(false)
    setProgress(0)
    setAvailable(true)
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.load()
    }
  }, [bite.id])

  function handleTimeUpdate() {
    const audio = audioRef.current
    if (!audio || !audio.duration) return
    setProgress((audio.currentTime / audio.duration) * 100)
  }

  function handleEnded() {
    setPlaying(false)
    setProgress(100)
  }

  function handleError() {
    setAvailable(false)
    setPlaying(false)
  }

  function togglePlay() {
    const audio = audioRef.current
    if (!audio) return
    if (playing) {
      audio.pause()
      setPlaying(false)
    } else {
      audio.play().then(() => setPlaying(true)).catch(() => setAvailable(false))
    }
  }

  function handleSeek(e) {
    const audio = audioRef.current
    if (!audio || !audio.duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    audio.currentTime = ratio * audio.duration
    setProgress(ratio * 100)
  }

  const cat = categories[bite.category]

  return (
    <div className="player">
      <audio
        ref={audioRef}
        src={bite.audio}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        onError={handleError}
        preload="metadata"
      />

      <div className="player-category" style={{ color: cat.color }}>
        {cat.label}
      </div>

      <blockquote className="player-quote">
        &ldquo;{bite.quote}&rdquo;
      </blockquote>

      <div className="player-context">
        <span className="player-episode">{bite.episode}</span>
        <span className="player-sep">·</span>
        <span>{bite.context}</span>
      </div>

      {!available && (
        <div className="player-unavailable">
          Audio not yet available — clips are being sourced
        </div>
      )}

      {available && (
        <div
          className="player-progress"
          onClick={handleSeek}
          role="progressbar"
          aria-valuenow={Math.round(progress)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className="player-progress-fill" style={{ width: `${progress}%`, background: cat.color }} />
        </div>
      )}

      <div className="player-controls">
        <button className="ctrl-btn ctrl-secondary" onClick={onPrev} aria-label="Previous">
          &#9664;&#9664;
        </button>
        <button
          className="ctrl-btn ctrl-primary"
          onClick={togglePlay}
          disabled={!available}
          aria-label={playing ? 'Pause' : 'Play'}
          style={{ background: cat.color }}
          dangerouslySetInnerHTML={{ __html: playing ? '&#9646;&#9646;' : '&#9654;' }}
        />
        <button className="ctrl-btn ctrl-secondary" onClick={onNext} aria-label="Next">
          &#9654;&#9654;
        </button>
      </div>

      <div className="player-actions">
        <button className="random-btn" onClick={onRandom}>
          &#9684; Random
        </button>
        <button className="copy-btn" onClick={copyLink}>
          {copied ? '✓ Copied!' : '⛓ Copy link'}
        </button>
      </div>

      <div className="player-counter">
        {currentIndex + 1} / {totalCount}
      </div>
    </div>
  )
}
