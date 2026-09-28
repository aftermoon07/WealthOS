"use client";
import { useState, useEffect } from "react";

export default function SetupPage() {
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "error">("idle");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("wealthos_backend_url");
    if (stored) setBackendUrl(stored);
  }, []);

  const testConnection = async (url: string) => {
    setStatus("checking");
    try {
      const res = await fetch(`${url}/api/dashboard`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        setStatus("ok");
        return true;
      }
      setStatus("error");
      return false;
    } catch {
      setStatus("error");
      return false;
    }
  };

  const handleSave = async () => {
    const clean = backendUrl.replace(/\/$/, "");
    const ok = await testConnection(clean);
    if (ok) {
      localStorage.setItem("wealthos_backend_url", clean);
      setSaved(true);
      setTimeout(() => (window.location.href = "/"), 1000);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "2rem",
      background: "var(--bg-primary)",
    }}>
      <div className="glass-card" style={{ maxWidth: "520px", width: "100%", padding: "2.5rem" }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{
            width: "64px", height: "64px",
            borderRadius: "16px",
            background: "linear-gradient(135deg, var(--brand-primary), var(--brand-accent))",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "2rem", margin: "0 auto 1rem",
          }}>💰</div>
          <h1 className="heading-2">Connect to WealthOS</h1>
          <p className="text-secondary" style={{ marginTop: "0.5rem", fontSize: "0.9rem" }}>
            WealthOS runs privately on your own machine. Enter the URL of your local backend to get started.
          </p>
        </div>

        {/* Setup steps */}
        <div style={{
          background: "var(--bg-secondary)",
          borderRadius: "12px",
          padding: "1.25rem",
          marginBottom: "1.5rem",
          fontSize: "0.85rem",
          lineHeight: "1.8",
          color: "var(--text-secondary)",
        }}>
          <strong style={{ color: "var(--text-primary)", display: "block", marginBottom: "0.5rem" }}>
            🚀 Quick Start (2 commands)
          </strong>
          <code style={{ display: "block", background: "rgba(0,0,0,0.3)", padding: "0.75rem", borderRadius: "8px", fontSize: "0.8rem", lineHeight: "2" }}>
            git clone https://github.com/aftermoon07/WealthOS<br/>
            cd WealthOS/backend<br/>
            uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
          </code>
          <p style={{ marginTop: "0.75rem", fontSize: "0.8rem" }}>
            Then paste your backend URL below. If running locally, it&apos;s <code>http://localhost:8000</code>.
          </p>
        </div>

        {/* URL input */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <label className="text-secondary" style={{ fontSize: "0.85rem", fontWeight: 500 }}>
            Backend URL
          </label>
          <input
            type="url"
            value={backendUrl}
            onChange={e => { setBackendUrl(e.target.value); setStatus("idle"); setSaved(false); }}
            placeholder="http://localhost:8000"
            style={{
              padding: "0.75rem 1rem",
              borderRadius: "10px",
              border: `1px solid ${status === "ok" ? "#10b981" : status === "error" ? "#ef4444" : "var(--border-color)"}`,
              background: "var(--bg-secondary)",
              color: "var(--text-primary)",
              fontSize: "0.95rem",
              outline: "none",
              transition: "border-color 0.2s",
            }}
          />

          {/* Status feedback */}
          {status === "checking" && (
            <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>⏳ Connecting to backend...</p>
          )}
          {status === "ok" && (
            <p style={{ color: "#10b981", fontSize: "0.85rem" }}>✅ Connected! Redirecting to dashboard...</p>
          )}
          {status === "error" && (
            <p style={{ color: "#ef4444", fontSize: "0.85rem" }}>
              ❌ Could not reach backend. Make sure it&apos;s running and the URL is correct.
            </p>
          )}

          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={status === "checking" || saved}
            style={{ marginTop: "0.25rem" }}
          >
            {status === "checking" ? "Connecting..." : saved ? "Connected! ✓" : "Connect & Open Dashboard"}
          </button>
        </div>

        {/* Privacy note */}
        <p style={{
          marginTop: "1.5rem",
          fontSize: "0.75rem",
          color: "var(--text-secondary)",
          textAlign: "center",
          opacity: 0.7,
        }}>
          🔒 Your financial data never leaves your machine. This site only connects to your local backend.
        </p>
      </div>
    </div>
  );
}
