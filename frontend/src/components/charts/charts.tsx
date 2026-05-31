import React from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const ORANGE = '#ffb800';
const BLUE = '#00c8ff';
const PURPLE = '#a855f7';
const GREEN = '#00ff94';
const RED = '#ff4466';

export const CHART_COLORS = { ORANGE, BLUE, PURPLE, GREEN, RED };

// Lightweight inline sparkline for KPI cards.
export const Sparkline: React.FC<{ data: number[]; color?: string; height?: number }> = ({
  data,
  color = ORANGE,
  height = 32,
}) => {
  if (!data || data.length === 0) return null;
  const w = 120;
  const h = height;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1 || 1);
  const pts = data.map((v, i) => `${i * step},${h - ((v - min) / span) * (h - 4) - 2}`);
  const d = `M ${pts.join(' L ')}`;
  const area = `${d} L ${w},${h} L 0,${h} Z`;
  const gid = `sg-${color.replace('#', '')}`;
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.25} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
};

const tooltipStyle = {
  background: 'rgba(10,10,12,0.95)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
  fontSize: 11,
  fontFamily: 'var(--font-mono)',
  color: '#f5f5f7',
};

interface SeriesPoint {
  [k: string]: string | number;
}

// Dual-line area chart (e.g. Hetzner vs AWS routing / throughput).
export const DualAreaChart: React.FC<{
  data: SeriesPoint[];
  xKey: string;
  aKey: string;
  bKey?: string;
  height?: number;
}> = ({ data, xKey, aKey, bKey, height = 220 }) => (
  <ResponsiveContainer width="100%" height={height}>
    <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
      <defs>
        <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={ORANGE} stopOpacity={0.35} />
          <stop offset="100%" stopColor={ORANGE} stopOpacity={0} />
        </linearGradient>
        <linearGradient id="gb" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={BLUE} stopOpacity={0.3} />
          <stop offset="100%" stopColor={BLUE} stopOpacity={0} />
        </linearGradient>
      </defs>
      <XAxis dataKey={xKey} tick={{ fill: '#636366', fontSize: 9, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} />
      <YAxis tick={{ fill: '#636366', fontSize: 9, fontFamily: 'var(--font-mono)' }} axisLine={false} tickLine={false} width={28} />
      <Tooltip contentStyle={tooltipStyle} />
      <Area type="monotone" dataKey={aKey} stroke={ORANGE} strokeWidth={2} fill="url(#ga)" />
      {bKey && <Area type="monotone" dataKey={bKey} stroke={BLUE} strokeWidth={2} fill="url(#gb)" />}
    </AreaChart>
  </ResponsiveContainer>
);

export const MonoLineChart: React.FC<{
  data: SeriesPoint[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
}> = ({ data, xKey, yKey, color = ORANGE, height = 200 }) => (
  <ResponsiveContainer width="100%" height={height}>
    <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
      <XAxis dataKey={xKey} tick={{ fill: '#636366', fontSize: 9 }} axisLine={false} tickLine={false} />
      <YAxis tick={{ fill: '#636366', fontSize: 9 }} axisLine={false} tickLine={false} width={28} />
      <Tooltip contentStyle={tooltipStyle} />
      <Line type="monotone" dataKey={yKey} stroke={color} strokeWidth={2} dot={false} />
    </LineChart>
  </ResponsiveContainer>
);

export const MonoBarChart: React.FC<{
  data: SeriesPoint[];
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
}> = ({ data, xKey, yKey, color = PURPLE, height = 200 }) => (
  <ResponsiveContainer width="100%" height={height}>
    <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
      <XAxis dataKey={xKey} tick={{ fill: '#636366', fontSize: 9 }} axisLine={false} tickLine={false} />
      <YAxis tick={{ fill: '#636366', fontSize: 9 }} axisLine={false} tickLine={false} width={28} />
      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
      <Bar dataKey={yKey} fill={color} radius={[2, 2, 0, 0]} />
    </BarChart>
  </ResponsiveContainer>
);
