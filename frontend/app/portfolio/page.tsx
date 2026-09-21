"use client";
import { useEffect, useState } from "react";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";
import "./Portfolio.css";

const COLORS = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#10b981", "#f59e0b"];

function fmt(v: string | number) {
  const n = parseFloat(String(v));
  if (isNaN(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function pct(v: string | number) {
  const n = parseFloat(String(v));
  if (isNaN(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

type Holding = {
  ticker: string; name: string; investment_type: string; sector?: string;
  quantity: string; average_cost: string; current_price: string;
  market_value: string; unrealized_pnl: string; unrealized_pnl_pct: string;
  price_source: string;
};

type PortfolioSummary = {
  total_invested: string; portfolio_value: string;
  unrealized_pnl: string; unrealized_pnl_pct: string;
  realized_pnl: string; dividend_income: string;
  xirr: string; xirr_confidence: string; xirr_reason: string;
  asset_allocation: Record<string, string>;
  holding_count: number; market_data_source: string;
};

type AngelOneStatus = {
  credentials_configured: boolean;
  last_sync: string | null;
  holdings_count: number;
  connected: boolean;
  error: string | null;
};

export default function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [allocation, setAllocation] = useState<Record<string, string>>({});
  const [angelStatus, setAngelStatus] = useState<AngelOneStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);

  async function fetchAll() {
    try {
      const [sumRes, holdRes, allocRes, aoRes] = await Promise.all([
        fetch("/api/portfolio/summary"),
        fetch("/api/portfolio/holdings"),
        fetch("/api/portfolio/allocation"),
        fetch("/api/integrations/angelone/status"),
      ]);
      const [sumData, holdData, allocData, aoData] = await Promise.all([
        sumRes.json(), holdRes.json(), allocRes.json(), aoRes.json(),
      ]);
      setSummary(sumData);
      setHoldings(holdData.holdings || []);
      setAllocation(allocData.asset_allocation || {});
      setAngelStatus(aoData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchAll(); }, []);

  async function handleSync() {
    setSyncing(true);
    try {
      const res = await fetch("/api/integrations/angelone/sync", { method: "POST" });
      const data = await res.json();
      if (data.status === "synced") {
        await fetchAll();
      } else {
        alert(data.message || "Sync skipped: credentials not configured.");
      }
    } finally {
      setSyncing(false);
    }
  }

  const pieData = Object.entries(allocation).map(([name, value]) => ({
    name, value: parseFloat(value),
  }));

  if (loading) return (
    <div className="container" style={{ paddingTop: "5rem", textAlign: "center" }}>
      <div className="loader"></div>
    </div>
  );

  return (
    <div className="container animate-fade-in">
      {/* Header */}
      <div className="flex-row space-between" style={{ marginBottom: "2rem" }}>
        <div>
          <h1 className="heading-1 text-gradient">Portfolio</h1>
          <p className="text-body">Live investment analysis powered by your brokerage data</p>
        </div>
        <div className="flex-row gap-md">
          <div className={`badge ${angelStatus?.credentials_configured ? "badge-success" : "badge-warning"}`}>
            {angelStatus?.credentials_configured
              ? `AngelOne ✓ ${angelStatus.last_sync ? `Last sync: ${angelStatus.last_sync}` : "Connected"}`
              : "AngelOne: Credentials not set"}
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSync}
            disabled={syncing}
            id="angelone-sync-btn"
          >
            {syncing ? "Syncing..." : "⟳ Sync AngelOne"}
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid-cards stagger-1" style={{ marginBottom: "2rem" }}>
        <div className="glass-panel kpi-card">
          <span className="text-body">Portfolio Value</span>
          <div className="heading-2">₹{fmt(summary?.portfolio_value || 0)}</div>
          <span className="text-small">Invested: ₹{fmt(summary?.total_invested || 0)}</span>
        </div>
        <div className="glass-panel kpi-card">
          <span className="text-body">Unrealized P&amp;L</span>
          <div className={`heading-2 ${parseFloat(summary?.unrealized_pnl || "0") >= 0 ? "value-positive" : "value-negative"}`}>
            ₹{fmt(summary?.unrealized_pnl || 0)}
          </div>
          <span className="text-small">{pct(summary?.unrealized_pnl_pct || 0)}</span>
        </div>
        <div className="glass-panel kpi-card">
          <span className="text-body">XIRR (Annualized Return)</span>
          <div className="heading-2 value-positive">{summary?.xirr}%</div>
          <span className={`badge ${summary?.xirr_confidence === "HIGH" ? "badge-success" : "badge-warning"}`}>
            {summary?.xirr_confidence}
          </span>
        </div>
        <div className="glass-panel kpi-card">
          <span className="text-body">Realized P&amp;L</span>
          <div className={`heading-2 ${parseFloat(summary?.realized_pnl || "0") >= 0 ? "value-positive" : "value-negative"}`}>
            ₹{fmt(summary?.realized_pnl || 0)}
          </div>
          <span className="text-small">Dividends: ₹{fmt(summary?.dividend_income || 0)}</span>
        </div>
      </div>

      {/* Charts Row */}
      <div className="dashboard-grid stagger-2" style={{ marginBottom: "2rem" }}>
        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>Asset Allocation</h2>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%" cy="50%"
                innerRadius={70} outerRadius={110}
                paddingAngle={4}
                dataKey="value"
                label={({ name, value }) => `${name} ${value.toFixed(1)}%`}
                labelLine={false}
              >
                {pieData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} contentStyle={{ background: "#121316", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>Holdings Count</h2>
          <div className="holdings-stats flex-col gap-md">
            {pieData.map((item, i) => (
              <div key={i} className="flex-row space-between">
                <div className="flex-row gap-sm">
                  <div className="dot" style={{ background: COLORS[i % COLORS.length] }}></div>
                  <span className="text-body">{item.name}</span>
                </div>
                <span className="value-neutral">{item.value.toFixed(1)}%</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: "2rem", padding: "1rem", background: "rgba(99,102,241,0.05)", borderRadius: 8, border: "1px solid rgba(99,102,241,0.1)" }}>
            <p className="text-small" style={{ lineHeight: 1.8 }}>
              <strong style={{ color: "var(--text-primary)" }}>XIRR:</strong> {summary?.xirr}%<br />
              <strong style={{ color: "var(--text-primary)" }}>Confidence:</strong> {summary?.xirr_reason}
            </p>
          </div>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="glass-panel content-card stagger-3">
        <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>
          Holdings ({holdings.length})
          {summary?.market_data_source === "DEMO" && (
            <span className="badge badge-warning" style={{ marginLeft: "1rem" }}>Demo Prices</span>
          )}
        </h2>
        <div className="table-wrapper">
          <table className="holdings-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Type</th>
                <th>Qty</th>
                <th>Avg Cost</th>
                <th>LTP</th>
                <th>Mkt Value</th>
                <th>Unrealized P&L</th>
                <th>Return</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, i) => {
                const pnl = parseFloat(h.unrealized_pnl);
                const positive = pnl >= 0;
                return (
                  <tr key={i}>
                    <td>
                      <div className="ticker-cell">
                        <span className="ticker-badge">{h.ticker.slice(0, 4)}</span>
                        <span className="text-body">{h.ticker}</span>
                      </div>
                    </td>
                    <td><span className="badge badge-info">{h.investment_type}</span></td>
                    <td>{fmt(h.quantity)}</td>
                    <td>₹{fmt(h.average_cost)}</td>
                    <td>₹{fmt(h.current_price)}</td>
                    <td><strong>₹{fmt(h.market_value)}</strong></td>
                    <td className={positive ? "value-positive" : "value-negative"}>
                      {positive ? "+" : ""}₹{fmt(h.unrealized_pnl)}
                    </td>
                    <td className={positive ? "value-positive" : "value-negative"}>
                      {pct(h.unrealized_pnl_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
