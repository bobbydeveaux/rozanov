import { useState, useCallback, useEffect } from 'react'
import { soundbites, categories } from './soundbites.js'
import Player from './components/Player.jsx'
import './App.css'

function getIndexFromHash(list) {
  const id = window.location.hash.slice(1)
  if (!id) return null
  const i = list.findIndex(b => b.id === id)
  return i >= 0 ? i : null
}

export default function App() {
  const firstWithAudio = soundbites.findIndex(b => b.hasAudio)
  const [activeCategory, setActiveCategory] = useState(null)

  const filtered = activeCategory
    ? soundbites.filter(b => b.category === activeCategory)
    : soundbites

  const initialIndex = getIndexFromHash(filtered) ?? (firstWithAudio >= 0 ? firstWithAudio : 0)
  const [currentIndex, setCurrentIndex] = useState(initialIndex)

  // Sync URL hash when clip changes
  useEffect(() => {
    const bite = filtered[currentIndex]
    if (bite) window.location.hash = bite.id
  }, [currentIndex, filtered])

  // Handle browser back/forward
  useEffect(() => {
    function onHashChange() {
      const i = getIndexFromHash(filtered)
      if (i !== null) setCurrentIndex(i)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [filtered])

  const safeMod = (n, mod) => ((n % mod) + mod) % mod

  const goTo = useCallback((index) => {
    setCurrentIndex(safeMod(index, filtered.length))
  }, [filtered.length])

  const goRandom = useCallback(() => {
    let next
    do { next = Math.floor(Math.random() * filtered.length) }
    while (filtered.length > 1 && next === currentIndex)
    setCurrentIndex(next)
  }, [filtered.length, currentIndex])

  const bite = filtered[currentIndex] ?? filtered[0]

  function handleCategoryChange(key) {
    setActiveCategory(key)
    // Try to keep same bite selected if it exists in new filter, else go to first
    const newFiltered = key ? soundbites.filter(b => b.category === key) : soundbites
    const same = newFiltered.findIndex(b => b.id === bite?.id)
    setCurrentIndex(same >= 0 ? same : 0)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="header-title">
            <span className="header-flag">🇷🇺</span>
            <div>
              <h1>Rozanov</h1>
              <p className="header-sub">Soundboard</p>
            </div>
          </div>
          <div className="header-show">
            <span>From</span>
            <a href="https://www.crave.ca" target="_blank" rel="noopener noreferrer">Heated Rivalry</a>
            <span className="header-sep">·</span>
            <a href="https://www.max.com" target="_blank" rel="noopener noreferrer">Watch on Max</a>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="filter-bar">
          <button
            className={`filter-chip ${!activeCategory ? 'active' : ''}`}
            onClick={() => handleCategoryChange(null)}
          >
            All ({soundbites.length})
          </button>
          {Object.entries(categories).map(([key, cat]) => {
            const count = soundbites.filter(b => b.category === key).length
            return (
              <button
                key={key}
                className={`filter-chip ${activeCategory === key ? 'active' : ''}`}
                style={activeCategory === key ? { borderColor: cat.color, color: cat.color } : {}}
                onClick={() => handleCategoryChange(key)}
              >
                {cat.label} ({count})
              </button>
            )
          })}
        </div>

        <Player
          bite={bite}
          onNext={() => goTo(currentIndex + 1)}
          onPrev={() => goTo(currentIndex - 1)}
          onRandom={goRandom}
          totalCount={filtered.length}
          currentIndex={currentIndex}
        />

        <div className="grid">
          {filtered.map((b, i) => {
            const cat = categories[b.category]
            return (
              <a
                key={b.id}
                href={`#${b.id}`}
                className={`grid-item ${i === currentIndex ? 'active' : ''}`}
                style={i === currentIndex ? { borderColor: cat.color } : {}}
                onClick={(e) => { e.preventDefault(); setCurrentIndex(i) }}
              >
                <span className="grid-cat" style={{ color: cat.color }}>
                  {cat.label}
                  {b.hasAudio && <span className="grid-audio-badge">▶ ready</span>}
                </span>
                <span className="grid-quote">&ldquo;{b.quote.length > 60 ? b.quote.slice(0, 60) + '…' : b.quote}&rdquo;</span>
                <span className="grid-ep">{b.episode.split(' — ')[0]}</span>
              </a>
            )
          })}
        </div>
      </main>

      <footer className="footer">
        <p>
          Unofficial fan project. Not affiliated with, endorsed by, or connected to{' '}
          <a href="https://www.crave.ca" target="_blank" rel="noopener noreferrer">Crave</a>
          {' '}or{' '}
          <a href="https://www.max.com" target="_blank" rel="noopener noreferrer">HBO Max</a>.
          All audio clips are property of Bell Media / Warner Bros. Discovery.
        </p>
        <p>
          Copyright concerns?{' '}
          <a href="mailto:copyright@rozanov.stackramp.io">copyright@rozanov.stackramp.io</a>
        </p>
        <p className="footer-cta">
          Support the show — watch <strong>Heated Rivalry</strong> on{' '}
          <a href="https://www.crave.ca" target="_blank" rel="noopener noreferrer">Crave</a> (Canada) or{' '}
          <a href="https://www.max.com" target="_blank" rel="noopener noreferrer">Max</a> (US &amp; international)
        </p>
      </footer>
    </div>
  )
}
