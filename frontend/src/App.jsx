import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('reviewer');
  const [demoMode, setDemoMode] = useState(true);
  const [repoPath, setRepoPath] = useState('');
  const [scanMode, setScanMode] = useState('pulled');
  const [compressionLevel, setCompressionLevel] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [diagLoading, setDiagLoading] = useState(false);
  
  // Settings State
  const [settings, setSettings] = useState({
    use_gpu_server: false,
    api_key: '',
    upstream_api_key: ''
  });
  const [showSettings, setShowSettings] = useState(false);

  // Analysis Results State
  const [results, setResults] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [cachedFiles, setCachedFiles] = useState({});

  // Diagnostic Results State
  const [diagResults, setDiagResults] = useState(null);

  // History State
  const [history, setHistory] = useState([]);

  // Load configuration and history on mount
  useEffect(() => {
    fetchSettings();
    fetchHistory();
    fetchCachedFiles();
    
    // Poll for live stats from active IDE sessions
    const interval = setInterval(() => {
      fetchHistory();
      fetchCachedFiles();
    }, 3000);
    
    return () => clearInterval(interval);
  }, []);

  const fetchCachedFiles = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/cached-files');
      if (res.ok) {
        const data = await res.json();
        setCachedFiles(data);
      }
    } catch (e) {
      console.error("Failed to fetch cached files:", e);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/settings');
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (e) {
      console.error("Failed to fetch settings from backend:", e);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/history');
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (e) {
      console.error("Failed to fetch history:", e);
    }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('http://127.0.0.1:8000/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        const data = await res.json();
        setSettings(data.settings);
        setShowSettings(false);
        alert("Settings saved successfully!");
      }
    } catch (e) {
      alert("Failed to save settings: " + e.message);
    }
  };

  const runAnalysis = async () => {
    setLoading(true);
    setResults(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_path: repoPath,
          demo_mode: demoMode,
          compression_level: compressionLevel,
          scan_mode: scanMode
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setResults(data);
        if (data.files && Object.keys(data.files).length > 0) {
          setSelectedFile(Object.keys(data.files)[0]);
        }
        fetchHistory(); // refresh graph data
      } else {
        const err = await res.json();
        alert("Analysis failed: " + err.detail);
      }
    } catch (e) {
      alert("Failed to reach backend server. Ensure FastAPI is running on port 8000!");
    } finally {
      setLoading(false);
    }
  };

  const runDiagnostics = async () => {
    setDiagLoading(true);
    setDiagResults(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/diagnose', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setDiagResults(data);
        alert("Diagnostic audit complete! feedback.md updated in workspace.");
      }
    } catch (e) {
      alert("Failed to run diagnostics: " + e.message);
    } finally {
      setDiagLoading(false);
    }
  };

  // Helper to format markdown review simply
  const formatMarkdown = (text) => {
    if (!text) return "";
    let html = text
      .replace(/### (.*)/g, '<h3>$1</h3>')
      .replace(/## (.*)/g, '<h2>$1</h2>')
      .replace(/# (.*)/g, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Highlighting parser for code blocks
    html = html.replace(/```(python|diff|javascript|yaml)?([\s\S]*?)```/g, (match, lang, code) => {
      let highlighted = code.trim();
      if (lang === 'python') {
        highlighted = highlighted
          // Escape HTML characters in raw code first to prevent injection issues
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          // Highlight comments
          .replace(/(#.*)/g, '<span class="code-comment">$1</span>')
          // Highlight strings
          .replace(/(".*?")/g, '<span class="code-string">$1</span>')
          .replace(/('.*?')/g, '<span class="code-string">$1</span>')
          // Highlight keywords
          .replace(/\b(def|class|return|try|except|raise|import|from|assert|if|else|elif|in|for|while|as|pass)\b/g, '<span class="code-keyword">$1</span>')
          // Highlight builtins
          .replace(/\b(print|ValueError|Exception|len|str|int|float|dict|list|set|round)\b/g, '<span class="code-builtin">$1</span>')
          // Highlight literals
          .replace(/\b(None|True|False)\b/g, '<span class="code-literal">$1</span>');
      } else if (lang === 'diff') {
        highlighted = highlighted
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .split('\n')
          .map(line => {
            if (line.startsWith('+')) {
              return `<span class="diff-addition">${line}</span>`;
            } else if (line.startsWith('-')) {
              return `<span class="diff-deletion">${line}</span>`;
            }
            return line;
          })
          .join('\n');
      } else {
        highlighted = highlighted.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      }
      return `<pre class="code-block ${lang || ''}"><code>${highlighted}</code></pre>`;
    });

    return html.replace(/\n/g, '<br/>');
  };

  // Render SVG charts
  const renderSavingsChart = () => {
    if (history.length === 0) return null;
    const padding = 40;
    const width = 500;
    const height = 150;
    const maxVal = 100;
    
    const points = history.map((run, i) => {
      const x = padding + (i * (width - 2 * padding)) / (history.length - 1 || 1);
      const y = height - padding - (run.savings * (height - 2 * padding)) / maxVal;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg width="100%" height="150" viewBox={`0 0 ${width} ${height}`} className="svg-chart">
        {/* Grid lines */}
        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#1e293b" />
        <line x1={padding} y1={height/2} x2={width - padding} y2={height/2} stroke="#1e293b" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#334155" />
        
        {/* Chart Line */}
        <polyline
          fill="none"
          stroke="url(#chart-glow)"
          strokeWidth="3"
          points={points}
        />
        
        {/* Data points */}
        {history.map((run, i) => {
          const x = padding + (i * (width - 2 * padding)) / (history.length - 1 || 1);
          const y = height - padding - (run.savings * (height - 2 * padding)) / maxVal;
          return (
            <g key={i} className="chart-dot-group">
              <circle cx={x} cy={y} r="5" fill="#00f2fe" />
              <text x={x} y={y - 10} fill="#f1f5f9" fontSize="9" textAnchor="middle">
                {run.savings}%
              </text>
            </g>
          );
        })}
        
        {/* Gradients */}
        <defs>
          <linearGradient id="chart-glow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#4facfe" />
            <stop offset="100%" stopColor="#00f2fe" />
          </linearGradient>
        </defs>
      </svg>
    );
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="main-header glass-panel">
        <div className="logo-section">
          <span className="logo-icon">⚡</span>
          <div className="logo-text">
            <h1>GitLean</h1>
            <p>Token-Efficient Pulled Changes Reviewer</p>
          </div>
        </div>

        <div className="control-bar">
          <div className="mode-toggle">
            <span className={demoMode ? 'active' : ''} onClick={() => setDemoMode(true)}>Demo Workspace</span>
            <span className={!demoMode ? 'active' : ''} onClick={() => setDemoMode(false)}>Local Repository</span>
          </div>

          {!demoMode && (
            <>
              <input 
                type="text" 
                placeholder="Absolute path to Git repository..." 
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                className="repo-input"
              />
              <select 
                value={scanMode} 
                onChange={(e) => setScanMode(e.target.value)}
                className="repo-input"
                style={{ width: '150px' }}
              >
                <option value="pulled">Pulled Changes (HEAD@{1})</option>
                <option value="local">Local Changes (Uncommitted)</option>
              </select>
            </>
          )}

          <button className="btn btn-primary pulse-glow" onClick={runAnalysis} disabled={loading}>
            {loading ? 'Analyzing...' : scanMode === 'pulled' ? 'Scan Pulled Changes' : 'Scan Local Changes'}
          </button>

          <button className="btn btn-settings" onClick={() => setShowSettings(true)}>
            ⚙️ Settings
          </button>
        </div>
      </header>

      {/* Settings Modal */}
      {showSettings && (
        <div className="modal-backdrop">
          <div className="modal-content glass-panel">
            <h2>Paritok & Upstream Configuration</h2>
            <form onSubmit={saveSettings}>
              <div className="form-group">
                <label>Compression Strategy</label>
                <div className="toggle-container">
                  <input 
                    type="checkbox" 
                    id="use_gpu"
                    checked={settings.use_gpu_server}
                    onChange={(e) => setSettings({...settings, use_gpu_server: e.target.checked})}
                  />
                  <label htmlFor="use_gpu">Use Hosted GPU Server (Paritok.com)</label>
                </div>
              </div>

              <div className="form-group">
                <label>Paritok API Key (pk_live_...)</label>
                <input 
                  type="password" 
                  value={settings.api_key} 
                  onChange={(e) => setSettings({...settings, api_key: e.target.value})}
                  placeholder="Enter API Key from paritok.com dashboard"
                />
              </div>

              <div className="form-group">
                <label>Anthropic API Key (Claude Code Upstream)</label>
                <input 
                  type="password" 
                  value={settings.upstream_api_key} 
                  onChange={(e) => setSettings({...settings, upstream_api_key: e.target.value})}
                  placeholder="Optional: Enter Claude key for real upstream API calls"
                />
                <p className="help-text">If left blank, GitLean uses the high-fidelity mock reviewer for the demo.</p>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSettings(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Settings</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Main Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Left Panel: Analytics & Navigation */}
        <aside className="sidebar-panel">
          {/* Savings Analytics */}
          <div className="glass-panel stat-card">
            <h3>Token Savings Analytics</h3>
            <div className="stat-value">
              <span className="number">{results ? results.savings_ratio : '74.9'}%</span>
              <span className="label">Average Context Reduction</span>
            </div>
            
            <div className="metrics-subgrid">
              <div className="metric">
                <span className="title">Tokens Sent</span>
                <span className="value text-muted">{results ? results.compressed_tokens : '3,120'}</span>
              </div>
              <div className="metric">
                <span className="title">Original Tokens</span>
                <span className="value text-muted">{results ? results.original_tokens : '12,450'}</span>
              </div>
              <div className="metric">
                <span className="title">Input Cost Saved</span>
                <span className="value text-success">${results ? results.cost_saved : '0.056'}</span>
              </div>
            </div>

            {renderSavingsChart()}
          </div>

          {/* Navigation Tabs */}
          <nav className="glass-panel nav-panel">
            <button className={activeTab === 'reviewer' ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab('reviewer')}>
              📋 Git Pull Review Summary
            </button>
            <button className={activeTab === 'visualizer' ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab('visualizer')}>
              🔍 Split-Screen Context Visualizer
            </button>
          </nav>
        </aside>

        {/* Right Panel: Content Area */}
        <main className="content-panel glass-panel">
          {/* Tab 1: Code Reviewer */}
          {activeTab === 'reviewer' && (
            <div className="tab-content reviewer-tab">
              <h2>📋 Git Pull Review Summary</h2>
              <p className="tab-subtitle">Summarizing and reviewing changes introduced in the latest git pull operation</p>
              
              {results ? (
                <div className="review-report-markdown" dangerouslySetInnerHTML={{ __html: formatMarkdown(results.review_report) }} />
              ) : (
                <div className="empty-state">
                  <div className="icon">🚀</div>
                  <h3>No Pull Review Generated</h3>
                  <p>Click "Scan Pulled Changes" in the top bar to analyze updates and generate an AI review using Paritok compression.</p>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Context Visualizer */}
          {activeTab === 'visualizer' && (
            <div className="tab-content visualizer-tab">
              <h2>🔍 Split-Screen Context Visualizer</h2>
              <p className="tab-subtitle">Visualizing original source files vs. the semantic compression sent to the LLM</p>

              {(results?.files || Object.keys(cachedFiles).length > 0) ? (
                <div className="visualizer-container">
                  <div className="file-selector">
                    {Object.keys(results?.files || cachedFiles).map((filepath) => {
                      const fileInfo = results?.files?.[filepath] || cachedFiles[filepath];
                      return (
                        <button 
                          key={filepath}
                          className={(selectedFile === filepath || (!selectedFile && Object.keys(results?.files || cachedFiles)[0] === filepath)) ? 'file-item active' : 'file-item'}
                          onClick={() => setSelectedFile(filepath)}
                        >
                          📄 {filepath}
                          <span className="file-saving">-{fileInfo.savings_ratio}%</span>
                        </button>
                      );
                    })}
                  </div>

                  {(() => {
                    const currentFile = selectedFile || Object.keys(results?.files || cachedFiles)[0];
                    const fileInfo = results?.files?.[currentFile] || cachedFiles[currentFile];
                    if (!fileInfo) return null;
                    return (
                      <div className="split-view">
                        <div className="code-column">
                          <h4>Original Code ({fileInfo.original_tokens} tokens)</h4>
                          <pre className="code-display">
                            <code>{fileInfo.original_code}</code>
                          </pre>
                        </div>
                        <div className="code-column compressed">
                          <h4>Paritok Compressed ({fileInfo.compressed_tokens} tokens)</h4>
                          <pre className="code-display">
                            <code>
                              {fileInfo.compressed_code.split('\n').map((line, i) => {
                                // Visually flag collapsed lines for the viewer
                                if (line.includes('//') || line.includes('...') || line.includes('omitted')) {
                                  return <span key={i} className="line-omitted">{line}\n</span>;
                                }
                                return line + '\n';
                              })}
                            </code>
                          </pre>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="icon">🔍</div>
                  <h3>No Files Analyzed Yet</h3>
                  <p>Run a local review in the dashboard, or configure your IDE coding assistant (like Antigravity) to use the GitLean proxy to see compression in real-time!</p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
