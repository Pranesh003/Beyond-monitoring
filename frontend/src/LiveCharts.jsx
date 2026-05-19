import React, { useEffect, useRef } from 'react';
import {
  Chart,
  LineController, LineElement, PointElement, LinearScale,
  TimeScale, Filler, Tooltip, Legend,
  CategoryScale,
} from 'chart.js';

Chart.register(
  LineController, LineElement, PointElement, LinearScale,
  TimeScale, Filler, Tooltip, Legend, CategoryScale
);

// Colour palette per pod
const POD_COLORS = {
  'api-gateway':     { line: '#38bdf8', fill: 'rgba(56,189,248,0.15)' },
  'user-service':    { line: '#a78bfa', fill: 'rgba(167,139,250,0.15)' },
  'payment-service': { line: '#34d399', fill: 'rgba(52,211,153,0.15)' },
  'rogue-pod':       { line: '#f87171', fill: 'rgba(248,113,113,0.18)' },
};
const DEFAULT_COLOR = { line: '#94a3b8', fill: 'rgba(148,163,184,0.1)' };

function formatLabel(ts) {
  const d = new Date(ts);
  return `${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
}

// ── Rolling Line Chart (CPU or Mem) ──────────────────────────────────────────
export function RollingLineChart({ title, timeseries, metricKey, unit, formatValue }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const ctx = ref.current.getContext('2d');

    // Build datasets
    const pods = Object.keys(timeseries);
    const labels = pods.length
      ? timeseries[pods[0]].timestamps.map(formatLabel)
      : [];

    const datasets = pods.map(pod => {
      const c = POD_COLORS[pod] || DEFAULT_COLOR;
      return {
        label: pod,
        data: timeseries[pod][metricKey].map(v =>
          metricKey === 'mem' ? +(v / 1_000_000).toFixed(1) : +v.toFixed(6)
        ),
        borderColor: c.line,
        backgroundColor: c.fill,
        borderWidth: 1.8,
        pointRadius: 0,
        tension: 0.4,
        fill: false,
      };
    });

    if (chartRef.current) {
      // Update existing chart
      chartRef.current.data.labels = labels;
      chartRef.current.data.datasets = datasets;
      chartRef.current.update('none');
      return;
    }

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: '#94a3b8', boxWidth: 10, font: { size: 10 } },
          },
          tooltip: {
            backgroundColor: 'rgba(15,23,42,0.9)',
            titleColor: '#e2e8f0',
            bodyColor: '#94a3b8',
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}${unit}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#475569', font: { size: 9 }, maxTicksLimit: 8 },
            grid: { color: 'rgba(255,255,255,0.04)' },
          },
          y: {
            ticks: { color: '#475569', font: { size: 9 },
              callback: v => `${v}${unit}` },
            grid: { color: 'rgba(255,255,255,0.04)' },
          },
        },
      },
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [timeseries]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <p style={{ color: '#94a3b8', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>
        {title}
      </p>
      <div style={{ flex: 1, minHeight: 0 }}>
        <canvas ref={ref} />
      </div>
    </div>
  );
}

// ── Sparkline (single pod, single metric) ────────────────────────────────────
export function Sparkline({ values, color }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!ref.current || !values?.length) return;
    const ctx = ref.current.getContext('2d');
    const labels = values.map((_, i) => i);

    if (chartRef.current) {
      chartRef.current.data.labels = labels;
      chartRef.current.data.datasets[0].data = values;
      chartRef.current.update('none');
      return;
    }

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          data: values,
          borderColor: color,
          backgroundColor: color.replace(')', ', 0.15)').replace('rgb', 'rgba'),
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.4,
          fill: true,
        }],
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
      },
    });

    return () => { chartRef.current?.destroy(); chartRef.current = null; };
  }, [values, color]);

  return <canvas ref={ref} style={{ width: '100%', height: '100%' }} />;
}
