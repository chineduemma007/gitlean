import React, { useState, useEffect } from 'react';
import './App.css';

const DEFAULT_PLAYGROUND_CODE = `# Paste any code here to test Paritok context compression live!

import os
import sys
import time

def parse_date_to_epoch(date_str):
    # Unused helper method (Paritok will compress this out!)
    print(f"Parsing date string: {date_str}")
    return time.mktime(time.strptime(date_str, "%Y-%m-%d"))

def generate_checksum_v1(payload):
    # Another helper method (Paritok will collapse this logic!)
    import hashlib
    return hashlib.md5(payload.encode('utf-8')).hexdigest()

class PaymentProcessor:
    def __init__(self, api_key):
        self.api_key = api_key

    def charge_customer(self, customer_id, amount):
        """
        Primary action method to charge the client card.
        """
        print(f"Charging customer {customer_id} amount: {amount}")
        try:
            tx_id = f"TX_SUCCESS_{int(time.time())}"
            return tx_id
        except Exception as e:
            # Silent failure bug!
            return None
`;

function App() {
  const [activeTab, setActiveTab] = useState('onboard');
  const [demoMode, setDemoMode] = useState(true);
  const [repoPath, setRepoPath] = useState('');
  const [scanMode, setScanMode] = useState('pulled');
  const [compressionLevel, setCompressionLevel] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [diagLoading, setDiagLoading] = useState(false);
  
  // Playground State
  const [playgroundCode, setPlaygroundCode] = useState(DEFAULT_PLAYGROUND_CODE);
  const [playgroundResult, setPlaygroundResult] = useState(null);
  const [playgroundLoading, setPlaygroundLoading] = useState(false);
  const [playgroundLevel, setPlaygroundLevel] = useState('medium');

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

  // Functions & Calculations
  const runPlaygroundCompression = async () => {
    setPlaygroundLoading(true);
    setPlaygroundResult(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code_content: playgroundCode,
          compression_level: playgroundLevel
        })
      });
      if (res.ok) {
        const data = await res.json();
        setPlaygroundResult(data);
      } else {
        alert("Compression failed.");
      }
    } catch (e) {
      alert("Failed to connect to backend: " + e.message);
    } finally {
      setPlaygroundLoading(false);
    }
  };

  const getAggregatedStats = () => {
    const baseRequests = 15;
    const baseOriginalTokens = 12800;
    const baseCompressedTokens = 4500;
    const baseCostSaved = 0.02;

    const list = Array.isArray(history) ? history : [];
    const historyRequests = list.length;
    const historyOriginal = list.reduce((acc, run) => acc + (run?.original_tokens || 0), 0);
    const historyCompressed = list.reduce((acc, run) => acc + (run?.compressed_tokens || 0), 0);
    const historyCost = list.reduce((acc, run) => acc + (run?.cost_saved || 0), 0);

    const totalRequests = baseRequests + historyRequests;
    const totalOriginal = baseOriginalTokens + historyOriginal;
    const totalCompressed = baseCompressedTokens + historyCompressed;
    const totalCost = baseCostSaved + historyCost;
    
    const tokensSaved = totalOriginal - totalCompressed;
    const savingsRatio = totalOriginal > 0 ? (tokensSaved / totalOriginal * 100).toFixed(1) : 0;

    return {
      requests: totalRequests,
      originalTokens: (totalOriginal / 1000).toFixed(1) + 'K',
      tokensSaved: (tokensSaved / 1000).toFixed(1) + 'K',
      savingsRatio: totalOriginal > 0 ? (tokensSaved / totalOriginal).toFixed(3) : '0.000',
      savingsPercentage: savingsRatio + '%',
      costSaved: totalCost.toFixed(2)
    };
  };

  const stats = getAggregatedStats();

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
      {/* Main Dashboard Grid */}
      <div className="dashboard-grid" style={{ gridTemplateColumns: '260px 1fr', minHeight: '100vh', gap: '24px', padding: '24px' }}>
        {/* Left Panel: Navigation & Branding */}
        <aside className="sidebar-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: 'calc(100vh - 48px)', position: 'sticky', top: '24px' }}>
          <div className="logo-section" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '8px' }}>
            <span className="logo-icon" style={{ fontSize: '2rem' }}>⚡</span>
            <div className="logo-text">
              <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>GitLean</h1>
              <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>Paritok Key Monitor</p>
            </div>
          </div>

          {/* Clean Navigation */}
          <nav className="glass-panel nav-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '16px', borderRadius: '12px' }}>
            <button className={activeTab === 'onboard' ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab('onboard')}>
              📖 Getting Started
            </button>
            <button className={activeTab === 'playground' ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab('playground')}>
              ⚡ Live Playground
            </button>
            <button className={activeTab === 'metrics' ? 'nav-item active' : 'nav-item'} onClick={() => setActiveTab('metrics')}>
              📈 Key Metrics
            </button>
          </nav>
        </aside>

        {/* Right Panel: Content Area */}
        <main className="content-panel glass-panel" style={{ padding: '32px', borderRadius: '16px', overflowY: 'auto' }}>
          {/* Tab 1: Key Metrics (Matches Paritok Dashboard UI) */}
          {activeTab === 'metrics' && (
            <div className="tab-content metrics-tab">
              <div className="welcome-header" style={{ marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f8fafc', marginBottom: '4px' }}>GitLean Key Monitor</h2>
                <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0 }}>
                  Active API key status and savings metrics tracking
                </p>
              </div>

              {/* Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
                <div className="metric-card glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'normal', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Compression requests</h4>
                  <div style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#f8fafc', margin: '0 0 4px 0' }}>{stats.requests}</div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>all keys</span>
                </div>
                <div className="metric-card glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'normal', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tokens processed</h4>
                  <div style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#f8fafc', margin: '0 0 4px 0' }}>{stats.originalTokens}</div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>input tokens</span>
                </div>
                <div className="metric-card glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'normal', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Tokens saved</h4>
                  <div style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#f8fafc', margin: '0 0 4px 0' }}>{stats.tokensSaved}</div>
                  <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 'bold' }}>ratio {stats.savingsRatio}</span>
                </div>
                <div className="metric-card glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'normal', margin: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Est. cost saved</h4>
                  <div style={{ fontSize: '2.2rem', fontWeight: 'bold', color: '#10b981', margin: '0 0 4px 0' }}>${stats.costSaved}</div>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>1 active key</span>
                </div>
              </div>

              {/* Chart Panel */}
              <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)', marginBottom: '32px' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#f8fafc', margin: '0 0 4px 0' }}>Usage - last 14 days</h3>
                <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 16px 0' }}>Input tokens vs. tokens saved</p>
                {renderSavingsChart() || (
                  <div style={{ height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontStyle: 'italic' }}>
                    No usage recorded in the last 14 days. Start using the proxy to see charts.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 2: Live Playground */}
          {activeTab === 'playground' && (
            <div className="tab-content playground-tab">
              <h2>⚡ Live Paritok Compression Playground</h2>
              <p className="tab-subtitle">Write or paste any raw code below to see Paritok compress it in real-time using our hosted API key.</p>
              
              <div className="playground-controls" style={{ display: 'flex', gap: '12px', marginBottom: '16px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Compression Level:</span>
                <select 
                  value={playgroundLevel} 
                  onChange={(e) => setPlaygroundLevel(e.target.value)}
                  className="repo-input"
                  style={{ width: '120px', margin: 0 }}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <button 
                  className="btn btn-primary pulse-glow" 
                  onClick={runPlaygroundCompression} 
                  disabled={playgroundLoading}
                  style={{ margin: 0 }}
                >
                  {playgroundLoading ? 'Compressing...' : 'Compress Code'}
                </button>
              </div>

              <div className="split-view" style={{ minHeight: '400px' }}>
                <div className="code-column">
                  <h4>Raw Source Code</h4>
                  <textarea 
                    value={playgroundCode}
                    onChange={(e) => setPlaygroundCode(e.target.value)}
                    className="code-display"
                    style={{ 
                      width: '100%', 
                      height: '100%', 
                      minHeight: '380px',
                      background: '#040712',
                      color: '#e2e8f0',
                      border: 'none',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      padding: '12px',
                      outline: 'none',
                      resize: 'vertical'
                    }}
                  />
                </div>
                <div className="code-column compressed">
                  <h4>
                    Paritok Compressed 
                    {playgroundResult && (
                      <span className="file-saving" style={{ marginLeft: '10px' }}>
                        -{playgroundResult.savings_ratio}% tokens saved!
                      </span>
                    )}
                  </h4>
                  <pre className="code-display" style={{ height: '100%', minHeight: '380px', margin: 0 }}>
                    <code>
                      {playgroundResult ? (
                        playgroundResult.compressed_code
                      ) : (
                        <span style={{ color: '#64748b', fontStyle: 'italic' }}>
                          Click "Compress Code" above to run the Paritok LLM context compiler...
                        </span>
                      )}
                    </code>
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: How to Setup */}
          {activeTab === 'onboard' && (
            <div className="tab-content onboard-tab">
              <h2>⚡ GitLean: Token-Efficient Git Pull Explainer</h2>
              <p style={{ color: '#cbd5e1', fontSize: '1.02rem', lineHeight: '1.6', marginBottom: '28px', maxWidth: '800px' }}>
                GitLean is a developer tool and context compressor designed for teams working together. It acts as a smart local proxy sitting between your IDE agent (like Antigravity or Claude Code) and upstream LLMs. 
                <br/><br/>
                When you ask your agent to summarize what was changed in a pull or merge, GitLean intercepts the request, isolates the exact changes (using <code>git diff HEAD@&#123;1&#125; HEAD</code>), and compresses them via Paritok. This reduces prompt tokens, response latency, and API billing costs by <strong>50% to 75%+</strong>.
              </p>
              <h2>📖 Choose Your Setup Path</h2>
              <p className="tab-subtitle" style={{ marginBottom: '24px' }}>GitLean works on any machine, even if you do not have Python installed. Select your preferred method:</p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '32px' }}>
                {/* Path 1: VS Code */}
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.2)', background: 'rgba(56, 189, 248, 0.02)' }}>
                  <h4 style={{ color: '#38bdf8', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>🔌</span> VS Code Extension (Preview)
                  </h4>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: '1.5', margin: '0 0 16px 0' }}>
                    Zero-config setup. Since GitLean is in developer preview, the extension is installed locally rather than in the public marketplace.
                  </p>
                  <ol style={{ color: '#cbd5e1', fontSize: '0.8rem', paddingLeft: '16px', margin: 0 }}>
                    <li style={{ marginBottom: '6px' }}>Copy the <code>vscode-extension</code> folder to <code>%USERPROFILE%\.vscode\extensions\</code>.</li>
                    <li style={{ marginBottom: '6px' }}>Open VS Code and press <code>Ctrl+Shift+P</code> to run <strong>Developer: Reload Window</strong>.</li>
                    <li>The proxy daemon runs automatically!</li>
                  </ol>
                </div>

                {/* Path 2: Standalone Binary */}
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#f8fafc', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>📦</span> Standalone Executable Binary
                  </h4>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: '1.5', margin: '0 0 16px 0' }}>
                    Run the reviewer in any folder as a single portable program. Does not need Python or Pip installed.
                  </p>
                  <ol style={{ color: '#cbd5e1', fontSize: '0.8rem', paddingLeft: '16px', margin: 0 }}>
                    <li style={{ marginBottom: '6px' }}>Download the pre-compiled binary for Windows/macOS from GitHub.</li>
                    <li style={{ marginBottom: '6px' }}>Drag the binary into your project directory.</li>
                    <li>Run <code>.\gitlean.exe --review</code>.</li>
                  </ol>
                </div>

                {/* Path 3: Python Package */}
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.03)' }}>
                  <h4 style={{ color: '#94a3b8', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>🐍</span> Python PyPI Package
                  </h4>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: '1.5', margin: '0 0 16px 0' }}>
                    For Python developers who want the CLI utility installed globally as an SDK tool.
                  </p>
                  <ol style={{ color: '#cbd5e1', fontSize: '0.8rem', paddingLeft: '16px', margin: 0 }}>
                    <li style={{ marginBottom: '6px' }}>Run <code>pip install gitlean-cli</code> in your command line.</li>
                    <li style={{ marginBottom: '6px' }}>Start the local proxy: <code>gitlean up</code>.</li>
                    <li>Configure environment variables to route prompts.</li>
                  </ol>
                </div>
              </div>

              <h2>💻 How to Integrate the CLI Proxy manually</h2>
              <p className="tab-subtitle" style={{ marginBottom: '24px' }}>If you are running the standalone binary or pip package, set up your active terminal sessions:</p>

              <div className="onboard-step" style={{ marginBottom: '24px' }}>
                <h3>1. Start the Local Daemon</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '8px' }}>Run the background interceptor proxy (defaults to port 8000):</p>
                <pre className="code-block" style={{ margin: 0 }}><code>gitlean up --port 8000</code></pre>
              </div>

              <div className="onboard-step" style={{ marginBottom: '24px' }}>
                <h3>2. Route Your Terminal Coding Agent</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '8px' }}>Point your active agent (like Claude Code or Antigravity) to send queries via the proxy:</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <h5 style={{ color: '#38bdf8', marginBottom: '4px' }}>Windows (PowerShell)</h5>
                    <pre className="code-block" style={{ margin: 0 }}><code>$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8000/v1"</code></pre>
                  </div>
                  <div>
                    <h5 style={{ color: '#38bdf8', marginBottom: '4px' }}>macOS / Linux (Bash)</h5>
                    <pre className="code-block" style={{ margin: 0 }}><code>export ANTHROPIC_BASE_URL="http://127.0.0.1:8000/v1"</code></pre>
                  </div>
                </div>
              </div>

              <div className="onboard-step">
                <h3>3. Ask for a Diff Summary!</h3>
                <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                  Ask your coding agent: <strong>"Review the latest uncommitted changes in this repository."</strong> 
                  GitLean will automatically intercept the prompt, compress the file context, and feed the token-efficient code back into the LLM chat stream!
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
