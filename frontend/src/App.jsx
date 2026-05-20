import React, { useState, useEffect, useRef } from 'react';
import {
  Activity, Server, Database, Network, ShieldAlert,
  CheckCircle, AlertTriangle, RefreshCw, FileText,
  MessageSquare, X, Send, Zap, Cpu, HardDrive, TrendingUp,
} from 'lucide-react';
import CytoscapeComponent from 'react-cytoscapejs';
import { RollingLineChart, Sparkline } from './LiveCharts';

const API = 'http://127.0.0.1:8000';

const POD_LINE_COLORS = {
  'api-gateway':     '#38bdf8',
  'user-service':    '#a78bfa',
  'payment-service': '#34d399',
  'rogue-pod':       '#f87171',
};

function AnimatedNumber({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);
  useEffect(() => {
    const steps = 12;
    const delta = (value - prev.current) / steps;
    let step = 0;
    const id = setInterval(() => {
      step++;
      setDisplay(p => +(p + delta).toFixed(decimals + 2));
      if (step >= steps) { clearInterval(id); setDisplay(value); }
    }, 25);
    prev.current = value;
    return () => clearInterval(id);
  }, [value]);
  return <span>{Number(display).toFixed(decimals)}</span>;
}

// ── Pod card with sparkline ──────────────────────────────────────────────────
const DYNAMIC_COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fb7185', '#fcd34d', '#f472b6', '#2dd4bf', '#fb923c'];

function getPodColor(pod) {
  if (POD_LINE_COLORS[pod]) return POD_LINE_COLORS[pod];
  let hash = 0;
  for (let i = 0; i < pod.length; i++) hash = pod.charCodeAt(i) + ((hash << 5) - hash);
  return DYNAMIC_COLORS[Math.abs(hash) % DYNAMIC_COLORS.length];
}

function PodCard({ pod, cpuValues, memValues }) {
  const isRogue = pod.includes('rogue-pod') || pod.includes('anomaly');
  const color = getPodColor(pod);
  const lastCpu = cpuValues?.[cpuValues.length - 1] ?? 0;
  const lastMem = memValues?.[memValues.length - 1] ?? 0;
  const memMB = (lastMem / 1_000_000).toFixed(0);

  return (
    <div className={`pod-card ${isRogue ? 'pod-card--rogue' : ''}`}>
      <div className="pod-card__header">
        <span className="pod-name">{pod}</span>
        {isRogue && <span className="badge badge--danger">ANOMALY</span>}
      </div>
      <div className="pod-card__metrics">
        <div className="pod-metric">
          <Cpu className="pod-metric__icon" size={12} />
          <span className="pod-metric__label">CPU</span>
          <span className="pod-metric__val" style={{ color }}>
            {(lastCpu * 1000).toFixed(1)} <span style={{ opacity: 0.6 }}>mc</span>
          </span>
        </div>
        <div className="pod-metric">
          <HardDrive className="pod-metric__icon" size={12} />
          <span className="pod-metric__label">MEM</span>
          <span className="pod-metric__val" style={{ color }}>
            {memMB} <span style={{ opacity: 0.6 }}>MB</span>
          </span>
        </div>
      </div>
      <div className="pod-sparkline">
        <Sparkline values={cpuValues?.map(v => v * 1000)} color={color} />
      </div>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────
export default function App() {
  const [anomalyData, setAnomalyData] = useState(null);
  const [topology, setTopology] = useState([]);
  const [logAnalysis, setLogAnalysis] = useState(null);
  const [timeseries, setTimeseries] = useState({});
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Chat
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { sender: 'ai', text: 'Hello! I am your Kubernetes AI Assistant. Ask me anything about your cluster health.' },
  ]);
  const chatEndRef = useRef(null);

  const fetchAll = async () => {
    try {
      const [anomRes, topoRes, logRes, tsRes, ovRes] = await Promise.all([
        fetch(`${API}/api/v1/anomalies`),
        fetch(`${API}/api/v1/topology`),
        fetch(`${API}/api/v1/logs/analysis`),
        fetch(`${API}/api/v1/metrics/timeseries`),
        fetch(`${API}/api/v1/cluster/overview`),
      ]);
      const [anomData, topoData, logData, tsData, ovData] = await Promise.all([
        anomRes.json(), topoRes.json(), logRes.json(), tsRes.json(), ovRes.json(),
      ]);
      setAnomalyData(anomData);
      setTopology(topoData.elements);
      setLogAnalysis(logData);
      setTimeseries(tsData);
      setOverview(ovData);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Fetch error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isChatOpen]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    const msg = chatMessage;
    setChatMessage('');
    setChatHistory(h => [...h, { sender: 'user', text: msg }, { sender: 'ai', text: '...', loading: true }]);
    try {
      const res = await fetch(`${API}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      setChatHistory(h => { const n = [...h]; n[n.length - 1] = { sender: 'ai', text: data.reply }; return n; });
    } catch {
      setChatHistory(h => { const n = [...h]; n[n.length - 1] = { sender: 'ai', text: 'Connection error.' }; return n; });
    }
  };

  const handleRemediate = async (podName) => {
    try {
      const res = await fetch(`${API}/api/v1/remediate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pod_name: podName }),
      });
      const data = await res.json();
      alert(`Auto-Remediation: ${data.message}`);
      fetchAll();
    } catch { alert('Failed to reach remediation agent.'); }
  };

  const totalPods   = anomalyData?.total_pods_analyzed ?? overview?.total_pods ?? 4;
  const anomaliesCount = anomalyData?.anomalies_detected ?? 0;
  const anomalies   = anomalyData?.anomalies ?? [];
  const statusOk    = anomaliesCount === 0;

  const cyStyles = [
    { 
      selector: 'node',               
      style: { 
        'background-color': '#3b82f6', 
        'label': 'data(label)', 
        'color': '#cbd5e1', 
        'font-size': '11px', 
        'font-weight': '600', 
        'text-valign': 'bottom', 
        'text-margin-y': 8,
        'width': 38, 
        'height': 38,
        'text-background-opacity': 0.8,
        'text-background-color': '#060d1a',
        'text-background-padding': '4px 6px',
        'text-background-shape': 'roundrectangle',
        'border-width': 2,
        'border-color': '#1e293b'
      } 
    },
    { 
      selector: 'edge',               
      style: { 
        'width': 2.5, 
        'line-color': '#475569', 
        'target-arrow-color': '#475569', 
        'target-arrow-shape': 'triangle', 
        'curve-style': 'bezier',
        'arrow-scale': 1.3
      } 
    },
    { 
      selector: 'node[type="database"]', 
      style: { 
        'background-color': '#8b5cf6', 
        'shape': 'barrel', 
        'width': 40, 
        'height': 40 
      } 
    },
    { 
      selector: 'node[type="ingress"]',  
      style: { 
        'background-color': '#10b981', 
        'shape': 'diamond', 
        'width': 42, 
        'height': 42,
        'border-color': '#047857'
      } 
    },
    { 
      selector: 'node[type="anomaly"]',  
      style: { 
        'background-color': '#ef4444', 
        'border-width': 2, 
        'border-color': '#fca5a5', 
        'width': 44, 
        'height': 44,
        'text-background-color': '#450a0a',
        'text-background-opacity': 0.9
      } 
    },
  ];

  return (
    <div className="app">
      {/* Ambient blobs */}
      <div className="blob blob--tl" />
      <div className={`blob blob--br ${statusOk ? 'blob--ok' : 'blob--err'}`} />

      {/* ── NAV ── */}
      <nav className="navbar">
        <div className="navbar__brand">
          <div className="brand-icon"><Activity size={18} /></div>
          <h1 className="brand-title">Kube AI Core</h1>
        </div>
        <div className="navbar__right">
          {loading && <RefreshCw size={14} className="spin" style={{ color: '#64748b' }} />}
          {lastUpdate && (
            <span className="update-badge">
              <span className={`dot ${statusOk ? 'dot--ok' : 'dot--err'}`} />
              Live · {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <span className="cluster-badge">minikube-dev</span>
        </div>
      </nav>

      {/* ── KPI ROW ── */}
      <div className="kpi-row">
        <div className="kpi-card">
          <Server size={16} className="kpi-icon" style={{ color: '#38bdf8' }} />
          <div>
            <p className="kpi-label">Nodes</p>
            <p className="kpi-value">3</p>
            <p className="kpi-sub" style={{ color: '#34d399' }}>All Healthy</p>
          </div>
        </div>
        <div className={`kpi-card ${!statusOk ? 'kpi-card--danger' : ''}`}>
          <Database size={16} className="kpi-icon" style={{ color: '#a78bfa' }} />
          <div>
            <p className="kpi-label">Pods Monitored</p>
            <p className="kpi-value"><AnimatedNumber value={totalPods} /></p>
            <p className={`kpi-sub ${statusOk ? '' : 'kpi-sub--danger'}`}>
              {statusOk ? 'Baseline Normal' : `${anomaliesCount} Anomaly Detected`}
            </p>
          </div>
        </div>
        <div className="kpi-card">
          <Cpu size={16} className="kpi-icon" style={{ color: '#f97316' }} />
          <div>
            <p className="kpi-label">Cluster CPU Rate</p>
            <p className="kpi-value">
              <AnimatedNumber value={+(( overview?.total_cpu_rate ?? 0) * 1000).toFixed(1)} decimals={1} />
              <span className="kpi-unit"> mc</span>
            </p>
            <p className="kpi-sub">millicores / sec</p>
          </div>
        </div>
        <div className="kpi-card">
          <HardDrive size={16} className="kpi-icon" style={{ color: '#fb7185' }} />
          <div>
            <p className="kpi-label">Cluster Memory</p>
            <p className="kpi-value">
              <AnimatedNumber value={overview?.total_mem_gb ?? 0} decimals={2} />
              <span className="kpi-unit"> GB</span>
            </p>
            <p className="kpi-sub">in-use</p>
          </div>
        </div>
        <div className="kpi-card">
          <TrendingUp size={16} className="kpi-icon" style={{ color: '#34d399' }} />
          <div>
            <p className="kpi-label">Anomaly Score</p>
            <p className="kpi-value" style={{ color: statusOk ? '#34d399' : '#f87171' }}>
              {statusOk ? '0' : anomaliesCount}
            </p>
            <p className="kpi-sub">{statusOk ? 'All Clear' : 'Requires Attention'}</p>
          </div>
        </div>
      </div>

      {/* ── MAIN GRID ── */}
      <main className="main-grid">

        {/* ── LEFT COLUMN ── */}
        <div className="col col--left">

          {/* Pod cards with sparklines */}
          <section className="panel">
            <h2 className="panel__title"><Activity size={14} /> Pod Live Metrics</h2>
            <div className="pod-grid">
              {Object.keys(timeseries).length > 0
                ? Object.entries(timeseries).map(([pod, data]) => (
                    <PodCard
                      key={pod}
                      pod={pod}
                      cpuValues={data.cpu}
                      memValues={data.mem}
                    />
                  ))
                : <p className="muted-text animate-pulse">Collecting metrics…</p>
              }
            </div>
          </section>

          {/* NLP log intelligence */}
          <section className="panel panel--flex1">
            <h2 className="panel__title"><FileText size={14} /> NLP Log Intelligence</h2>
            {logAnalysis ? (
              <div className="log-section">
                <p className="muted-text" style={{ fontSize: 11 }}>
                  Analyzed {logAnalysis.total_errors_analyzed} recent error logs
                </p>
                <div className="keyword-cloud">
                  {logAnalysis.nlp_extracted_keywords?.map(kw => (
                    <span key={kw} className="keyword">{kw}</span>
                  ))}
                </div>
                <div className="critical-log">{logAnalysis.sample_critical_log}</div>
              </div>
            ) : (
              <p className="muted-text animate-pulse">Running TF-IDF vectors…</p>
            )}
          </section>
        </div>

        {/* ── CENTER COLUMN ── */}
        <div className="col col--center">
          {/* CPU Timeseries Chart */}
          <section className="panel panel--chart">
            <h2 className="panel__title"><Cpu size={14} /> CPU Usage — Live Rolling Window</h2>
            <div className="chart-area">
              {Object.keys(timeseries).length > 0
                ? <RollingLineChart
                    title="CPU Rate (millicores/sec)"
                    timeseries={timeseries}
                    metricKey="cpu"
                    unit="mc"
                  />
                : <p className="muted-text animate-pulse">Waiting for metrics…</p>
              }
            </div>
          </section>

          {/* Memory Timeseries Chart */}
          <section className="panel panel--chart">
            <h2 className="panel__title"><HardDrive size={14} /> Memory Usage — Live Rolling Window</h2>
            <div className="chart-area">
              {Object.keys(timeseries).length > 0
                ? <RollingLineChart
                    title="Memory (MB)"
                    timeseries={timeseries}
                    metricKey="mem"
                    unit="MB"
                  />
                : <p className="muted-text animate-pulse">Waiting for metrics…</p>
              }
            </div>
          </section>

          {/* Topology Graph - Moved down below charts */}
          <section className="panel panel--topo">
            <h2 className="panel__title"><Network size={14} /> NetworkX Dependency Topology</h2>
            <div className="topo-area">
              {topology.length > 0
                ? <CytoscapeComponent
                    key={topology.map(el => el.data.id || (el.data.source + '-' + el.data.target)).join(',')}
                    elements={topology}
                    style={{ width: '100%', height: '100%' }}
                    layout={{
                      name: 'concentric',
                      concentric: function(node) {
                        return node.data('type') === 'ingress' ? 2 : 1;
                      },
                      levelWidth: function(nodes) {
                        return 1;
                      },
                      padding: 50,
                      animate: false
                    }}
                    stylesheet={cyStyles}
                    userZoomingEnabled={true}
                  />
                : <p className="muted-text animate-pulse">Building graph…</p>
              }
            </div>
          </section>
        </div>

        {/* ── RIGHT COLUMN ── */}
        <div className="col col--right">
          {/* Anomaly list with Auto-Heal */}
          {!statusOk && (
            <section className="panel panel--danger">
              <h2 className="panel__title"><Zap size={14} style={{ color: '#f87171' }} /> Actionable Anomalies</h2>
              <div className="anomaly-list">
                {anomalies.map((anom, i) => (
                  <div key={i} className="anomaly-card">
                    <div className="anomaly-card__header">
                      <span className="anomaly-pod">
                        <AlertTriangle size={12} /> {anom.pod}
                      </span>
                    </div>
                    <div className="anomaly-stats">
                      <span>CPU: {(anom.cpu_usage_core_rate * 1000).toFixed(1)} mc</span>
                      <span>MEM: {(anom.memory_usage_bytes / 1_000_000).toFixed(0)} MB</span>
                    </div>
                    <div className="anomaly-card__footer">
                      <p className="anomaly-reason"><ShieldAlert size={10} /> {anom.agent_reasoning}</p>
                      <button className="heal-btn" onClick={() => handleRemediate(anom.pod)}>
                        <Zap size={10} /> Auto-Heal
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Cluster status when healthy */}
          {statusOk && (
            <section className="panel panel--healthy">
              <CheckCircle size={20} style={{ color: '#34d399' }} />
              <p style={{ color: '#34d399', fontWeight: 600, marginTop: 8 }}>Cluster Healthy</p>
              <p className="muted-text" style={{ fontSize: 11, marginTop: 4 }}>
                All pods operating within baseline parameters.
              </p>
            </section>
          )}

          {/* Master AI Insight */}
          <section className={`panel panel--flex1 ${!statusOk ? 'panel--warning' : ''}`}>
            <h2 className="panel__title">
              <ShieldAlert size={14} style={{ color: statusOk ? '#34d399' : '#fbbf24' }} />
              Master AI Insight
            </h2>
            <div className="insight-box">
              {loading && !anomalyData
                ? <p className="muted-text animate-pulse">Connecting to LLM Orchestrator…</p>
                : anomalyData?.master_insight
                  ? <p className="insight-text">{anomalyData.master_insight}</p>
                  : <p className="muted-text">No insights available.</p>
              }
            </div>
          </section>
        </div>
      </main>

      {/* ── CHAT WIDGET ── */}
      <div className="chat-widget">
        {isChatOpen && (
          <div className="chat-panel">
            <div className="chat-panel__header">
              <span><MessageSquare size={14} /> AI SRE Assistant</span>
              <button onClick={() => setIsChatOpen(false)}><X size={16} /></button>
            </div>
            <div className="chat-panel__messages">
              {chatHistory.map((msg, i) => (
                <div key={i} className={`chat-msg chat-msg--${msg.sender}`}>
                  <div className={`chat-bubble chat-bubble--${msg.sender} ${msg.loading ? 'animate-pulse' : ''}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <form className="chat-panel__input" onSubmit={handleSendMessage}>
              <input
                value={chatMessage}
                onChange={e => setChatMessage(e.target.value)}
                placeholder="Ask about your cluster…"
              />
              <button type="submit" disabled={!chatMessage.trim()}><Send size={14} /></button>
            </form>
          </div>
        )}
        <button className={`chat-toggle ${isChatOpen ? 'chat-toggle--active' : ''}`}
          onClick={() => setIsChatOpen(v => !v)}>
          {isChatOpen ? <X size={22} /> : <MessageSquare size={22} />}
        </button>
      </div>
    </div>
  );
}
