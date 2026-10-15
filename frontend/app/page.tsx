"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart, Line, AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import "./Dashboard.css";

/* ── helpers ─────────────────────────────────────────────── */
function fmtINR(v: string | number | undefined, compact = false): string {
  const n = parseFloat(String(v ?? 0));
  if (isNaN(n)) return "—";
  if (compact) {
    if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
    if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(2)}L`;
  }
  return `₹${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}
function fmtPct(v: string | number | undefined): string {
  const n = parseFloat(String(v ?? 0));
  if (isNaN(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}
function sign(v: string | number | undefined): "pos" | "neg" | "zero" {
  const n = parseFloat(String(v ?? 0));
  return n > 0 ? "pos" : n < 0 ? "neg" : "zero";
}
function today(): string {
  return new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
}

/* ── types ───────────────────────────────────────────────── */
type DashboardData = {
  summary: Record<string, string>;
  top_spending_categories: { category: string; current_month: string; avg_3m?: string; mom_change_pct?: string }[];
  anomaly_count: number;
  recent_anomalies: { type: string; severity: string; description: string; date?: string }[];
  goals: { name: string; target: string; current: string; progress_pct: string; on_track: boolean }[];
  net_worth_history: { date: string; net_worth: string }[];
  market_data_source: string;
};

/* ── sparkline tooltip ───────────────────────────────────── */
function SparkTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="spark-tooltip">
      <span className="spark-tooltip-val">{fmtINR(payload[0].value, true)}</span>
    </div>
  );
}

/* ── skeleton ────────────────────────────────────────────── */
function Skeleton() {
  return (
    <div className="container dash-skeleton animate-fade-in">
      {/* Hero skeleton */}
      <div style={{ paddingTop: "2.5rem", marginBottom: "2rem" }}>
        <div className="skeleton" style={{ height: 12, width: 100, marginBottom: 16, borderRadius: 6 }} />
        <div className="skeleton" style={{ height: 64, width: 280, marginBottom: 12, borderRadius: 8 }} />
        <div className="skeleton" style={{ height: 24, width: 160, borderRadius: 20 }} />
      </div>
      {/* KPI grid skeleton */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 16, marginBottom: 32 }}>
        {[1,2,3,4,5].map(i => (
          <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "20px" }}>
            <div className="skeleton" style={{ height: 10, width: 60, marginBottom: 14, borderRadius: 4 }} />
            <div className="skeleton" style={{ height: 32, width: 110, marginBottom: 10, borderRadius: 6 }} />
            <div className="skeleton" style={{ height: 10, width: 80, borderRadius: 4 }} />
          </div>
        ))}
      </div>
      {/* Chart skeleton */}
      <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: "24px", marginBottom: 24 }}>
        <div className="skeleton" style={{ height: 14, width: 180, marginBottom: 20, borderRadius: 4 }} />
        <div className="skeleton" style={{ height: 200, borderRadius: 8 }} />
      </div>
    </div>
  );
}

/* ── main component ──────────────────────────────────────── */
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/dashboard")
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton />;

  if (error) return (
    <div className="container" style={{ paddingTop: "4rem", textAlign: "center" }}>
      <div style={{
        display: "inline-flex", flexDirection: "column", alignItems: "center",
        gap: "1rem", padding: "2.5rem", borderRadius: 16,
        background: "rgba(255,107,107,0.05)", border: "1px solid rgba(255,107,107,0.2)"
      }}>
        <span style={{ fontSize: "2rem" }}>⚠️</span>
        <p className="type-h3">Could not load dashboard data</p>
        <p className="type-body-sm">Check the backend is running.<br />({error})</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
      </div>
    </div>
  );

  const {
    summary,
    top_spending_categories,
    anomaly_count,
    recent_anomalies,
    goals,
    net_worth_history,
    market_data_source,
  } = data!;

  const chartData = net_worth_history.map(s => ({
    date: new Date(s.date).toLocaleDateString("en-IN", { month: "short", year: "2-digit" }),
    value: parseFloat(s.net_worth),
  }));

  const netWorthDelta = (() => {
    if (chartData.length < 2) return null;
    const prev = chartData[chartData.length - 2].value;
    const curr = chartData[chartData.length - 1].value;
    return { abs: curr - prev, pct: prev !== 0 ? ((curr - prev) / Math.abs(prev)) * 100 : 0 };
  })();

  const savingsRate = parseFloat(summary.savings_rate ?? "0");
  const isDemo = market_data_source === "DEMO";

  const kpis = [
    {
      label: "Portfolio",
      value: fmtINR(summary.portfolio_value, true),
      delta: fmtPct(summary.unrealized_pnl_pct) + " unrealized",
      deltaSign: sign(summary.unrealized_pnl_pct),
    },
    {
      label: "XIRR",
      value: fmtPct(summary.xirr),
      delta: "Annualized return",
      deltaSign: sign(summary.xirr),
    },
    {
      label: "Monthly Income",
      value: fmtINR(summary.income),
      delta: "This month",
      deltaSign: "pos" as const,
    },
    {
      label: "Expenses",
      value: fmtINR(summary.expenses),
      delta: `${savingsRate.toFixed(1)}% savings rate`,
      deltaSign: savingsRate >= 20 ? "pos" as const : "neg" as const,
    },
    {
      label: "Net Savings",
      value: fmtINR(summary.savings),
      delta: "This month",
      deltaSign: sign(summary.savings),
    },
  ];

  return (
    <div className="container animate-fade-in">

      {/* Demo banner */}
      {isDemo && (
        <div className="demo-banner" style={{ marginLeft: -48, marginRight: -48, width: "calc(100% + 96px)" }}>
          ⚡ Demo mode — prices are illustrative
        </div>
      )}

      {/* ── NET WORTH HERO ─────────────────────────────────── */}
      <section className="nw-hero">
        <div className="nw-hero-left">
          <div className="nw-hero-eyebrow">
            <p className="type-label" style={{ letterSpacing: "0.10em" }}>NET WORTH</p>
            <span className="badge badge-neutral">as of {today()}</span>
          </div>
          <div className="nw-hero-value">
            <span className="nw-currency">₹</span>
            <span className="nw-amount">
              {Math.abs(parseFloat(summary.net_worth ?? "0")).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </span>
          </div>
          {netWorthDelta && (
            <div className={`nw-delta ${sign(netWorthDelta.abs)}`}>
              {netWorthDelta.abs >= 0 ? "▲" : "▼"}&nbsp;
              {fmtINR(Math.abs(netWorthDelta.abs))}
              &nbsp;({Math.abs(netWorthDelta.pct).toFixed(1)}%) this month
            </div>
          )}
        </div>

        {/* Sparkline */}
        {chartData.length > 1 && (
          <div className="nw-sparkline" aria-hidden="true">
            <ResponsiveContainer width="100%" height={72}>
              <AreaChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={netWorthDelta && netWorthDelta.abs >= 0 ? "#00d4aa" : "#ff6b6b"} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={netWorthDelta && netWorthDelta.abs >= 0 ? "#00d4aa" : "#ff6b6b"} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={netWorthDelta && netWorthDelta.abs >= 0 ? "#00d4aa" : "#ff6b6b"}
                  strokeWidth={2}
                  fill="url(#sparkGrad)"
                  dot={false}
                />
                <Tooltip content={<SparkTooltip />} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* ── KPI GRID ─────────────────────────────────────────── */}
      <div className="kpi-grid animate-fade-in stagger-1">
        {kpis.map((k, i) => (
          <div key={i} className="kpi-card">
            <p className="kpi-card-label">{k.label}</p>
            <p className={`kpi-card-value${k.deltaSign === "pos" && i === 1 ? " value-positive" : k.deltaSign === "neg" && i === 1 ? " value-negative" : ""}`}>
              {k.value}
            </p>
            <p className={`kpi-card-delta ${k.deltaSign}`}>{k.delta}</p>
          </div>
        ))}
      </div>

      {/* ── NET WORTH HISTORY CHART ───────────────────────────── */}
      <section className="panel animate-fade-in stagger-2" style={{ marginBottom: "var(--space-6)" }}>
        <div className="panel-header">
          <div>
            <span className="type-h3">Net Worth History</span>
            <span className="type-caption" style={{ marginLeft: 12, color: "var(--text-tertiary)" }}>
              Last {chartData.length} months
            </span>
          </div>
          <span className="badge badge-neutral" style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem" }}>
            {chartData.length > 0 ? chartData[chartData.length - 1].date : "—"}
          </span>
        </div>
        <div className="panel-body" style={{ paddingTop: "var(--space-4)" }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d4aa" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#00d4aa" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "rgba(255,255,255,0.3)", fontFamily: "Inter" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "rgba(255,255,255,0.3)", fontFamily: "Inter" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={v => `₹${(v/1e5).toFixed(0)}L`}
                  width={48}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#00d4aa"
                  strokeWidth={2}
                  fill="url(#areaGrad)"
                  dot={false}
                  activeDot={{ r: 5, fill: "#00d4aa", stroke: "rgba(0,212,170,0.3)", strokeWidth: 4 }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div className="chart-tooltip">
                        <span className="chart-tooltip-label">{label}</span>
                        <span className="chart-tooltip-val">{fmtINR(payload[0].value as number)}</span>
                      </div>
                    );
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <p className="empty-state-title">No net worth history yet</p>
              <p className="empty-state-body">Import transactions to start tracking your net worth over time.</p>
            </div>
          )}
        </div>
      </section>

      {/* ── 2-COLUMN: SPENDING + ANOMALIES+GOALS ─────────────── */}
      <div className="two-col animate-fade-in stagger-3" style={{ marginBottom: "var(--space-6)" }}>

        {/* SPENDING */}
        <section className="panel">
          <div className="panel-header">
            <span className="type-h3">Top Spending</span>
            <Link href="/spending" className="btn btn-ghost" style={{ fontSize: "0.8125rem" }}>
              View all →
            </Link>
          </div>
          <div style={{ padding: "0 var(--space-6) var(--space-6)" }}>
            {top_spending_categories.length === 0 ? (
              <div className="empty-state" style={{ paddingTop: "var(--space-8)" }}>
                <p className="empty-state-title">No spending data</p>
                <p className="empty-state-body">Import bank transactions to see spending categories.</p>
              </div>
            ) : top_spending_categories.map((cat, i) => {
              const pct = top_spending_categories[0]?.current_month
                ? (parseFloat(cat.current_month) / parseFloat(top_spending_categories[0].current_month)) * 100
                : 0;
              return (
                <div key={i} className="spending-row">
                  <div className="spending-row-top">
                    <span className="type-body" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{cat.category}</span>
                    <span className="tabular" style={{ fontSize: "var(--type-body)", fontWeight: 600, color: "var(--text-primary)" }}>
                      {fmtINR(cat.current_month)}
                    </span>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 8, height: 4 }}>
                    <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  {cat.mom_change_pct && (
                    <p className={`spending-delta ${sign(cat.mom_change_pct)}`}>
                      {fmtPct(cat.mom_change_pct)} vs last month
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* ANOMALIES + GOALS */}
        <section style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>

          {/* Anomalies */}
          <div className="panel">
            <div className="panel-header">
              <span className="type-h3">Anomalies</span>
              {anomaly_count > 0 && (
                <span className="badge badge-negative">{anomaly_count} detected</span>
              )}
            </div>
            <div style={{ padding: "var(--space-4) var(--space-6) var(--space-5)" }}>
              {anomaly_count === 0 ? (
                <p style={{ fontSize: "var(--type-body-sm)", color: "var(--text-secondary)" }}>
                  ✓&nbsp; No unusual patterns this month
                </p>
              ) : (
                <div className="anomaly-list">
                  {recent_anomalies.map((a, i) => (
                    <div key={i} className={`anomaly-item severity-${a.severity?.toLowerCase() ?? "medium"}`}>
                      <p className="anomaly-desc">{a.description}</p>
                      {a.date && (
                        <p className="anomaly-date">
                          {new Date(a.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Goals */}
          <div className="panel">
            <div className="panel-header">
              <span className="type-h3">Goals</span>
              <span className="type-caption" style={{ color: "var(--text-tertiary)" }}>{goals.length} active</span>
            </div>
            <div style={{ padding: "var(--space-4) var(--space-6) var(--space-5)" }}>
              {goals.length === 0 ? (
                <p style={{ fontSize: "var(--type-body-sm)", color: "var(--text-secondary)" }}>
                  No goals defined yet.
                </p>
              ) : (
                <div className="goals-list">
                  {goals.map((g, i) => {
                    const pct = Math.min(100, parseFloat(g.progress_pct ?? "0"));
                    return (
                      <div key={i} className="goal-item">
                        <div className="goal-header">
                          <span className="type-body" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{g.name}</span>
                          <span className={`badge ${g.on_track ? "badge-positive" : "badge-negative"}`}>
                            {g.on_track ? "On Track" : "At Risk"}
                          </span>
                        </div>
                        <div className="goal-nums">
                          <span className="tabular" style={{ fontSize: "var(--type-body-sm)", color: "var(--text-primary)" }}>
                            {fmtINR(g.current, true)}
                          </span>
                          <span style={{ fontSize: "var(--type-caption)", color: "var(--text-tertiary)" }}>
                            &nbsp;of {fmtINR(g.target, true)} · {pct.toFixed(0)}%
                          </span>
                        </div>
                        <div className="progress-bar-bg" style={{ marginTop: 8 }}>
                          <div
                            className="progress-bar-fill"
                            style={{
                              width: `${pct}%`,
                              background: g.on_track
                                ? "linear-gradient(90deg, #00d4aa, #7c6ff7)"
                                : "linear-gradient(90deg, #ff6b6b, #ff8e8e)"
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

        </section>
      </div>

      {/* ── AI FINANCIAL INTELLIGENCE ─────────────────────────── */}
      <section className="intelligence-section animate-fade-in stagger-4">
        <div className="intelligence-inner">
          <div className="intelligence-header">
            <p className="type-label" style={{ letterSpacing: "0.10em", marginBottom: "var(--space-2)" }}>
              Financial Intelligence
            </p>
            <p className="type-h2" style={{ marginBottom: "var(--space-2)" }}>Ask WealthOS anything.</p>
            <p className="type-body-sm" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              Powered by Gemini · Grounded in your real financial data
            </p>
          </div>
          <div className="intelligence-chips">
            {[
              "What is my XIRR and how is my portfolio performing?",
              "Where am I spending the most this month?",
              "Am I on track with my financial goals?",
            ].map((q, i) => (
              <Link key={i} href={`/assistant?q=${encodeURIComponent(q)}`} className="intelligence-chip">
                {q}
              </Link>
            ))}
          </div>
          <Link href="/assistant" className="btn btn-primary" style={{ alignSelf: "flex-start" }}>
            Open Intelligence →
          </Link>
        </div>
      </section>

    </div>
  );
}
