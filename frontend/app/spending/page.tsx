"use client";
import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid, Cell,
} from "recharts";
import "./Spending.css";

const CATEGORY_COLORS: Record<string, string> = {
  "Food & Dining": "#f59e0b",
  "Shopping": "#8b5cf6",
  "Transport": "#6366f1",
  "Utilities": "#10b981",
  "Entertainment": "#ec4899",
  "Health": "#06b6d4",
  "Housing": "#f97316",
  "Travel": "#a78bfa",
  "Education": "#14b8a6",
};

function fmt(v: string | number) {
  const n = parseFloat(String(v));
  if (isNaN(n)) return "0";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

type Category = {
  category: string; current_month: string; avg_3m: string | null;
  avg_6m: string | null; mom_change: string | null;
};

type Anomaly = {
  transaction_id: number; description: string; amount: string;
  category: string; severity: string;
};

export default function SpendingPage() {
  const [spending, setSpending] = useState<any>(null);
  const [cashFlow, setCashFlow] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;

  useEffect(() => {
    async function fetchAll() {
      try {
        const [spRes, cfRes, anRes] = await Promise.all([
          fetch(`/api/analytics/spending?year=${year}&month=${month}`),
          fetch(`/api/analytics/cash-flow?year=${year}&month=${month}`),
          fetch(`/api/analytics/anomalies?year=${year}&month=${month}`),
        ]);
        const [sp, cf, an] = await Promise.all([spRes.json(), cfRes.json(), anRes.json()]);
        setSpending(sp);
        setCashFlow(cf);
        setAnomalies(an.anomalies || []);
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  if (loading) return (
    <div className="container" style={{ paddingTop: "5rem", textAlign: "center" }}>
      <div className="loader"></div>
    </div>
  );

  const categories: Category[] = spending?.categories || [];
  const topCategories = categories.slice(0, 8);
  const barData = topCategories.map(c => ({
    name: c.category.replace(/ &.*/g, ""),
    current: parseFloat(c.current_month),
    avg3m: c.avg_3m ? parseFloat(c.avg_3m) : 0,
    color: CATEGORY_COLORS[c.category] || "#6366f1",
  }));

  // Build 6-month trend data from cashFlow if available
  const trendData = cashFlow?.monthly_trend?.slice(-6).map((m: any) => ({
    month: m.month,
    income: parseFloat(m.income || 0),
    expenses: parseFloat(m.expenses || 0),
    savings: parseFloat(m.savings || 0),
  })) || [];

  const savingsRate = parseFloat(cashFlow?.savings_rate || 0);

  return (
    <div className="container animate-fade-in">
      <div style={{ marginBottom: "2rem" }}>
        <h1 className="heading-1 text-gradient">Spending Analysis</h1>
        <p className="text-body">
          {today.toLocaleString("en-IN", { month: "long" })} {year} — detailed category breakdown
        </p>
      </div>

      {/* Anomaly Banner */}
      {anomalies.length > 0 && (
        <div className="anomaly-banner stagger-1">
          <span className="anomaly-icon">⚠</span>
          <div>
            <strong>{anomalies.length} anomal{anomalies.length === 1 ? "y" : "ies"} detected</strong>
            <p className="text-small" style={{ marginTop: "0.25rem" }}>
              {anomalies[0]?.description} — ₹{fmt(anomalies[0]?.amount)}
            </p>
          </div>
          <div style={{ marginLeft: "auto" }}>
            {anomalies.slice(0, 3).map((a, i) => (
              <span key={i} className={`badge ${a.severity === "HIGH" ? "badge-danger" : "badge-warning"}`} style={{ marginLeft: "0.5rem" }}>
                {a.category}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid-cards stagger-2" style={{ marginBottom: "2rem" }}>
        <div className="glass-panel spending-kpi">
          <span className="text-body">Total Spending</span>
          <div className="heading-2 value-negative">₹{fmt(spending?.total_spending || 0)}</div>
        </div>
        <div className="glass-panel spending-kpi">
          <span className="text-body">Monthly Income</span>
          <div className="heading-2 value-positive">₹{fmt(cashFlow?.income || 0)}</div>
        </div>
        <div className="glass-panel spending-kpi">
          <span className="text-body">Savings Rate</span>
          <div className={`heading-2 ${savingsRate >= 20 ? "value-positive" : "value-negative"}`}>
            {savingsRate.toFixed(1)}%
          </div>
          <span className={`badge ${savingsRate >= 20 ? "badge-success" : "badge-warning"}`}>
            {savingsRate >= 20 ? "On Track" : "Below Target"}
          </span>
        </div>
        <div className="glass-panel spending-kpi">
          <span className="text-body">Top Category</span>
          <div className="heading-2">{categories[0]?.category || "—"}</div>
          <span className="text-small">₹{fmt(categories[0]?.current_month || 0)}</span>
        </div>
      </div>

      <div className="dashboard-grid stagger-3" style={{ marginBottom: "2rem" }}>
        {/* Category Bar Chart */}
        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>Spending by Category</h2>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={barData} layout="vertical" margin={{ left: 20, right: 30 }}>
              <XAxis type="number" tick={{ fill: "#6b6b76", fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#a0a0ab", fontSize: 12 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip
                formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "Amount"]}
                contentStyle={{ background: "#121316", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
              />
              <Bar dataKey="current" radius={[0, 6, 6, 0]} name="This Month">
                {barData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Category Details Table */}
        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>Category Details</h2>
          <div className="flex-col gap-sm">
            {categories.slice(0, 7).map((c, i) => {
              const mom = c.mom_change ? parseFloat(c.mom_change) : null;
              return (
                <div key={i} className="category-row">
                  <div className="flex-row space-between" style={{ marginBottom: "0.25rem" }}>
                    <span className="text-body" style={{ fontSize: "0.875rem", fontWeight: 500 }}>{c.category}</span>
                    <div className="flex-row gap-sm">
                      {mom !== null && (
                        <span className={`text-small ${mom > 15 ? "value-negative" : mom < -15 ? "value-positive" : ""}`}>
                          {mom > 0 ? "▲" : "▼"} {Math.abs(mom).toFixed(0)}%
                        </span>
                      )}
                      <span style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "0.875rem" }}>
                        ₹{fmt(c.current_month)}
                      </span>
                    </div>
                  </div>
                  {c.avg_3m && (
                    <span className="text-small">3M avg: ₹{fmt(c.avg_3m)}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 6-Month Income vs Spending Trend */}
      {trendData.length > 0 && (
        <div className="glass-panel content-card stagger-4">
          <h2 className="heading-3" style={{ marginBottom: "1.5rem" }}>6-Month Cash Flow Trend</h2>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trendData} margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
              <defs>
                <linearGradient id="income-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expense-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" tick={{ fill: "#6b6b76", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b6b76", fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} />
              <Tooltip
                formatter={(v: number) => `₹${v.toLocaleString("en-IN")}`}
                contentStyle={{ background: "#121316", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
              />
              <Area type="monotone" dataKey="income" stroke="#10b981" fill="url(#income-grad)" strokeWidth={2} name="Income" />
              <Area type="monotone" dataKey="expenses" stroke="#ef4444" fill="url(#expense-grad)" strokeWidth={2} name="Expenses" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
