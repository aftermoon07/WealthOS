"use client";
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import './Dashboard.css';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const response = await fetch('/api/dashboard');
        const json = await response.json();
        setData(json);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="container flex-row" style={{ justifyContent: 'center', height: '50vh' }}>
        <div className="loader"></div>
      </div>
    );
  }

  const { summary, top_spending_categories, anomaly_count, recent_anomalies, goals, net_worth_history } = data || {};

  const chartData = net_worth_history?.map((item: any) => ({
    date: new Date(item.date).toLocaleDateString('en-US', { month: 'short' }),
    value: parseFloat(item.net_worth),
  })) || [];

  return (
    <div className="container animate-fade-in">
      <div className="flex-row space-between" style={{ marginBottom: '2rem' }}>
        <div className="flex-col gap-sm">
          <h1 className="heading-1 text-gradient stagger-1">Financial Overview</h1>
          <p className="text-body stagger-2">Welcome back. Here is your latest financial intelligence.</p>
        </div>
      </div>

      <div className="grid-cards stagger-3">
        {/* Cash Flow Card */}
        <div className="glass-panel stat-card">
          <div className="stat-header">
            <span className="text-body">Monthly Savings</span>
            <span className={`badge ${summary?.savings_rate > 20 ? 'badge-success' : 'badge-warning'}`}>
              {summary?.savings_rate}% Rate
            </span>
          </div>
          <div className="stat-value heading-1">
            ₹{summary?.savings ? parseFloat(summary.savings).toLocaleString('en-IN') : '0'}
          </div>
          <div className="stat-footer text-small">
            <span className="value-positive">IN: ₹{parseFloat(summary?.income || 0).toLocaleString('en-IN')}</span>
            <span style={{ margin: '0 8px', color: 'var(--border-glass)' }}>|</span>
            <span className="value-negative">OUT: ₹{parseFloat(summary?.expenses || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>

        {/* Portfolio Card */}
        <div className="glass-panel stat-card">
          <div className="stat-header">
            <span className="text-body">Portfolio Value</span>
            <span className="badge badge-info">XIRR {summary?.xirr}%</span>
          </div>
          <div className="stat-value heading-1">
            ₹{summary?.portfolio_value ? parseFloat(summary.portfolio_value).toLocaleString('en-IN') : '0'}
          </div>
          <div className="stat-footer text-small">
            <span className="value-positive">+{summary?.unrealized_pnl_pct}% Unrealized</span>
          </div>
        </div>

        {/* Alerts Card */}
        <div className="glass-panel stat-card">
          <div className="stat-header">
            <span className="text-body">Anomalies Detected</span>
            {anomaly_count > 0 && <span className="badge badge-danger">{anomaly_count} New</span>}
          </div>
          <div className="stat-value heading-1">
            {anomaly_count}
          </div>
          <div className="stat-footer text-small">
            {anomaly_count > 0 ? (
              <span className="value-negative">{recent_anomalies?.[0]?.description}</span>
            ) : (
              <span className="value-positive">Everything looks normal</span>
            )}
          </div>
        </div>
      </div>

      {/* Net Worth History Chart */}
      <div className="glass-panel content-card stagger-4" style={{ marginTop: '2rem' }}>
        <h2 className="heading-3" style={{ marginBottom: '1.5rem' }}>Net Worth History</h2>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
              <YAxis 
                stroke="var(--text-secondary)" 
                tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                tickFormatter={(value) => `₹${(value / 100000).toFixed(1)}L`}
                width={80}
              />
              <Tooltip 
                contentStyle={{ background: "#121316", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, 'Net Worth']}
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#8b5cf6" 
                strokeWidth={3}
                dot={{ fill: '#8b5cf6', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#6366f1', stroke: '#fff' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="dashboard-grid stagger-4" style={{ marginTop: '2rem' }}>
        {/* Top Spending */}
        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: '1.5rem' }}>Top Spending Categories</h2>
          <div className="flex-col gap-md">
            {top_spending_categories?.map((cat: any, i: number) => (
              <div key={i} className="spending-row flex-row space-between">
                <span className="text-body font-500">{cat.category}</span>
                <span className="value-neutral">₹{parseFloat(cat.current_month).toLocaleString('en-IN')}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Goals Progress */}
        <div className="glass-panel content-card">
          <h2 className="heading-3" style={{ marginBottom: '1.5rem' }}>Goals Progress</h2>
          <div className="flex-col gap-md">
            {goals?.map((goal: any, i: number) => (
              <div key={i} className="goal-item flex-col gap-sm">
                <div className="flex-row space-between">
                  <span className="text-body font-500">{goal.name}</span>
                  <span className="text-small">{goal.progress_pct}%</span>
                </div>
                <div className="progress-bar-bg">
                  <div className="progress-bar-fill" style={{ width: `${goal.progress_pct}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
