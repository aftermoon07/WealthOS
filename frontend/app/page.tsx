"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LineChart, Line, ResponsiveContainer, Tooltip,
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
      <div className="skeleton" style={{ height: 14, width: 80, marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 52, width: 240, marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 18, width: 200, marginBottom: 48 }} />
      <div className="skeleton" style={{ height: 1, width: "100%", marginBottom: 40 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24 }}>
        {[1, 2, 3].map(i => (
          <div key={i}>
            <div className="skeleton" style={{ height: 11, width: 80, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 28, width: 140, marginBottom: 6 }} />
            <div className="skeleton" style={{ height: 13, width: 100 }} />
          </div>
        ))}
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
    <div className="container" style={{ paddingTop: "4rem" }}>
      <p className="type-h3" style={{ marginBottom: 8 }}>Could not load dashboard data.</p>
      <p className="type-body-sm" style={{ marginBottom: 24 }}>
        Check that the backend is running. ({error})
      </p>
      <button className="btn btn-ghost" onClick={() => window.location.reload()}>Retry</button>
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
    date: new Date(s.date).toLocaleDateString("en-IN", { month: "short" }),
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

  return (
    <div className="container animate-fade-in">

      {/* Demo banner */}
      {isDemo && (
        <div className="demo-banner" style={{ marginBottom: 0, marginLeft: -48, marginRight: -48, width: "calc(100% + 96px)" }}>
          Demo mode — prices are illustrative
        </div>
      )}

      {/* ── NET WORTH HERO ─────────────────────────────────── */}
      <section className="nw-hero">
        <div className="nw-hero-left">
          <p className="type-label" style={{ marginBottom: 10, letterSpacing: "0.06em" }}>NET WORTH</p>
          <div className="nw-hero-value">
            <span className="nw-currency">₹</span>
            <span className="nw-amount">
              {Math.abs(parseFloat(summary.net_worth ?? "0")).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            </span>
          </div>
          {netWorthDelta && (
            <p className={`nw-delta ${sign(netWorthDelta.abs)}`}>
              {netWorthDelta.abs >= 0 ? "▲" : "▼"}&nbsp;
              {fmtINR(Math.abs(netWorthDelta.abs))}&nbsp;
              ({Math.abs(netWorthDelta.pct).toFixed(1)}%) this month
            </p>
          )}
          <p className="type-caption" style={{ marginTop: 6, color: "var(--text-tertiary)" }}>
            as of {today()}
          </p>
        </div>

        {/* Sparkline — pure trend, no axes, no labels */}
        {chartData.length > 1 && (
          <div className="nw-sparkline" aria-hidden="true">
            <ResponsiveContainer width="100%" height={60}>
              <LineChart data={chartData} margin={{ top: 4, right: 0, left: 0, bottom: 4 }}>
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={netWorthDelta && netWorthDelta.abs >= 0 ? "var(--positive)" : "var(--negative)"}
                  strokeWidth={1.5}
                  dot={false}
                />
                <Tooltip content={<SparkTooltip />} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <hr className="divider" style={{ margin: "0 0 var(--space-10)" }} />

      {/* ── FINANCIAL METRICS ROW ───────────────────────────── */}
      <section className="metrics-row" style={{ marginBottom: "var(--space-12)" }}>
        <div className="metric-item">
          <p className="type-label">PORTFOLIO</p>
          <p className="metric-lg tabular">{fmtINR(summary.portfolio_value, true)}</p>
          <p className={`metric-delta ${sign(summary.unrealized_pnl_pct)}`}>
            {fmtPct(summary.unrealized_pnl_pct)} unrealized
          </p>
        </div>
        <div className="metric-divider" />
        <div className="metric-item">
          <p className="type-label">XIRR</p>
          <p className={`metric-lg tabular ${sign(summary.xirr)}`}>{fmtPct(summary.xirr)}&nbsp;<span className="xirr-unit">p.a.</span></p>
          <p className="type-caption" style={{ color: "var(--text-tertiary)", marginTop: 4 }}>Annualized return</p>
        </div>
        <div className="metric-divider" />
        <div className="metric-item">
          <p className="type-label">MONTHLY INCOME</p>
          <p className="metric-lg tabular value-positive">{fmtINR(summary.income)}</p>
          <p className="type-caption" style={{ color: "var(--text-tertiary)", marginTop: 4 }}>This month</p>
        </div>
        <div className="metric-divider" />
        <div className="metric-item">
          <p className="type-label">EXPENSES</p>
          <p className="metric-lg tabular value-negative">{fmtINR(summary.expenses)}</p>
          <p className={`metric-delta ${savingsRate >= 20 ? "pos" : "neg"}`}>
            {savingsRate.toFixed(1)}% savings rate
          </p>
        </div>
        <div className="metric-divider" />
        <div className="metric-item">
          <p className="type-label">NET SAVINGS</p>
          <p className={`metric-lg tabular ${sign(summary.savings)}`}>{fmtINR(summary.savings)}</p>
          <p className="type-caption" style={{ color: "var(--text-tertiary)", marginTop: 4 }}>This month</p>
        </div>
      </section>

      {/* ── NET WORTH HISTORY (full-width chart panel) ─────── */}
      <section className="panel" style={{ marginBottom: "var(--space-10)" }}>
        <div className="panel-header">
          <div>
            <span className="type-h3">Net Worth History</span>
            <span className="type-caption" style={{ marginLeft: 12, color: "var(--text-tertiary)" }}>
              Last {chartData.length} months
            </span>
          </div>
        </div>
        <div className="panel-body" style={{ paddingTop: "var(--space-4)" }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="var(--chart-1)"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 4, fill: "var(--chart-1)", strokeWidth: 0 }}
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
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <p className="empty-state-title">No net worth history yet</p>
              <p className="empty-state-body">Import transactions to start tracking your net worth over time.</p>
            </div>
          )}
        </div>
      </section>

      {/* ── 2-COLUMN: SPENDING + ANOMALIES ─────────────────── */}
      <div className="two-col" style={{ marginBottom: "var(--space-10)" }}>

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
                    <span className="type-body">{cat.category}</span>
                    <span className="tabular" style={{ fontSize: "var(--type-body)", fontWeight: 400 }}>
                      {fmtINR(cat.current_month)}
                    </span>
                  </div>
                  <div className="progress-bar-bg" style={{ marginTop: 6, height: 3 }}>
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

        {/* ANOMALIES */}
        <section>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-4)" }}>
            <span className="type-h3">Anomalies</span>
            {anomaly_count > 0 && (
              <span className="badge badge-negative">{anomaly_count} detected</span>
            )}
          </div>

          {anomaly_count === 0 ? (
            <p style={{ fontSize: "var(--type-body-sm)", color: "var(--text-secondary)", paddingTop: "var(--space-2)" }}>
              No unusual patterns detected this month.
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

          {/* GOALS below anomalies in right column */}
          <div style={{ marginTop: "var(--space-8)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "var(--space-4)" }}>
              <span className="type-h3">Goals</span>
            </div>
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
                        <span className="type-body" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{g.name}</span>
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
                      <div className="progress-bar-bg" style={{ marginTop: 6 }}>
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${pct}%`, background: g.on_track ? "var(--positive)" : "var(--negative)" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ── AI FINANCIAL INTELLIGENCE ───────────────────────── */}
      <section className="intelligence-section" style={{ marginBottom: "var(--space-12)" }}>
        <div className="intelligence-inner">
          <div className="intelligence-header">
            <p className="type-label" style={{ letterSpacing: "0.06em", marginBottom: "var(--space-2)" }}>
              FINANCIAL INTELLIGENCE
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
          <Link href="/assistant" className="btn btn-secondary" style={{ alignSelf: "flex-start" }}>
            Open Intelligence →
          </Link>
        </div>
      </section>

    </div>
  );
}
