import { useState, useRef, useEffect } from 'react'
import './App.css'
import EventBox from './EventBox'

function App() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    try {
      const resp = await fetch('http://localhost:8000/events')
      const data = await resp.json()
      if (data.success) {
        setHistory(data.events || [])
      }
    } catch (err) {
      console.error("Failed to fetch history:", err)
    }
  }


  const handleImageChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setImage(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result)
      }
      reader.readAsDataURL(file)
      setResult(null)
      setError(null)
    }
  }

  const handleExtract = async () => {
    if (!image) return

    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', image)

    try {
      const response = await fetch('http://localhost:8000/ocr', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      if (data.success) {
        setResult(data)
        fetchHistory() // Refresh history after new extraction
      } else {
        setError(data.error || 'Failed to extract text')
      }

    } catch (err) {
      setError('Connection error. Is the backend running?')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (result && result.full_text) {
      navigator.clipboard.writeText(result.full_text)
      alert('Copied to clipboard!')
    }
  }

  const triggerFileInput = () => {
    fileInputRef.current.click()
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>VisionText OCR</h1>
        <p>Extract high-precision text from any image using PaddleOCR & FastAPI</p>
      </header>

      <main className="main-content">
        {/* Event Display Section - Show structured data if available */}
        <section className="event-preview-section">
          <EventBox data={result?.structured ? {
            title: result.structured.event_name || "Event Title",
            date: result.structured.event_date || "Date Not Found",
            time: result.structured.event_time !== "N/A" ? result.structured.event_time : result.structured.entry_type,
            host: result.structured.organizer || "Host Not Found",
            location: result.structured.location || result.structured.website || "N/A",
            description: result.structured.highlights ? result.structured.highlights.join(" • ") : "No description",
            lineup: result.structured.highlights || []
          } : {
            title: "Upload Image to See Results",
            date: "Date Range",
            time: "Time / Entry",
            host: "Organizer Name",
            location: "Location",
            lineup: [],
            description: "Detailed event highlights will appear here."
          }} />
        </section>

        <div className="upload-card">
          <div className="drop-zone" onClick={triggerFileInput}>
            <input
              type="file"
              className="hidden-input"
              ref={fileInputRef}
              onChange={handleImageChange}
              accept="image/*"
            />
            {!preview ? (
              <>
                <span className="upload-icon">🖼️</span>
                <h3>Click to upload or drag and drop</h3>
                <p>PNG, JPG up to 10MB</p>
              </>
            ) : (
              <div className="preview-container">
                <img src={preview} alt="Preview" className="preview-image" />
              </div>
            )}
          </div>

          <div className="actions">
            <button
              className="btn btn-primary"
              onClick={handleExtract}
              disabled={!image || loading}
            >
              {loading && <span className="loading-spinner"></span>}
              {loading ? 'Analyzing...' : 'Extract Text'}
            </button>
            {preview && (
              <button className="btn btn-secondary" onClick={() => {
                setPreview(null)
                setImage(null)
                setResult(null)
              }}>
                Clear
              </button>
            )}
          </div>

          {error && <p style={{ color: '#ff6b6b', marginTop: '1rem' }}>{error}</p>}
        </div>

        {result && (
          <div className="result-card">
            <div className="result-header">
              <h2>Extracted Result</h2>
              <button className="btn btn-secondary" style={{ padding: '0.4rem 1rem' }} onClick={handleCopy}>
                📋 Copy All
              </button>
            </div>

            {/* Structured Variables Display */}
            <div style={{ marginTop: '1.5rem', background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
              <h3 style={{ marginBottom: '0.8rem', color: '#4facfe', fontSize: '1rem' }}>Smarter Event Classification:</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.8rem' }}>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Organizer:</strong> <span style={{ color: '#ccc' }}>{result.structured.organizer}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Event Name:</strong> <span style={{ color: '#ccc' }}>{result.structured.event_name}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Date:</strong> <span style={{ color: '#ccc' }}>{result.structured.event_date}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Time:</strong> <span style={{ color: '#ccc' }}>{result.structured.event_time}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Location:</strong> <span style={{ color: '#ccc' }}>{result.structured.location}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Entry Type:</strong> <span style={{ color: '#ccc' }}>{result.structured.entry_type}</span></div>
                <div style={{ fontSize: '0.9rem' }}><strong style={{ color: '#fff' }}>Website:</strong> <span style={{ color: '#ccc' }}>{result.structured.website}</span></div>
              </div>
              {result.structured.highlights && (
                <div style={{ marginTop: '1rem' }}>
                  <strong style={{ color: '#fff' }}>Event Highlights:</strong>
                  <ul style={{ margin: '0.5rem 0 0 1.2rem', color: '#ccc', fontSize: '0.85rem' }}>
                    {result.structured.highlights.map((h, i) => <li key={i}>{h}</li>)}
                  </ul>
                </div>
              )}
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {result.data && result.data.map((item, idx) => (
                <span key={idx} style={{
                  fontSize: '0.8rem',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: 'rgba(79, 172, 254, 0.1)',
                  border: '1px solid rgba(79, 172, 254, 0.2)',
                  color: '#4facfe'
                }}>
                  {item.text} ({Math.round(item.confidence * 100)}%)
                </span>
              ))}
            </div>
          </div>
        )}

        {/* History Section */}
        {history.length > 0 && (
          <section className="history-section" style={{ marginTop: '3rem', width: '100%', maxWidth: '1000px' }}>
            <h2 style={{ color: '#fff', marginBottom: '1.5rem', textAlign: 'center' }}>Processed History (Stored in MongoDB)</h2>
            <div className="history-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
              {history.map((item) => (
                <div key={item._id} className="history-card" onClick={() => setResult(item)} style={{
                  padding: '1.2rem',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, background 0.2s'
                }}>
                  <h4 style={{ color: '#4facfe', marginBottom: '0.5rem' }}>{item.event_details.event_name}</h4>
                  <p style={{ fontSize: '0.85rem', color: '#888' }}>{new Date(item.timestamp).toLocaleString()}</p>
                  <p style={{ fontSize: '0.9rem', color: '#ccc', marginTop: '0.5rem' }}>📍 {item.event_details.location}</p>
                </div>
              ))}
            </div>
          </section>
        )}

      </main>

      <footer className="footer">
        Powered by KloudBuild Technologies • 2026
      </footer>
    </div>
  )
}

export default App
