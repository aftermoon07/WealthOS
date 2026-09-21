"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import ConnectDataModal from "./ConnectDataModal";
import "./Navbar.css";

const NAV_LINKS = [
  { name: "Dashboard",     href: "/" },
  { name: "Portfolio",     href: "/portfolio" },
  { name: "Spending",      href: "/spending" },
  { name: "Intelligence",  href: "/assistant" },
];

type AOStatus = { connected: boolean; credentials_configured: boolean; last_sync: string | null };

export default function Navbar() {
  const pathname = usePathname();
  const [modalOpen, setModalOpen]   = useState(false);
  const [menuOpen, setMenuOpen]     = useState(false);
  const [aoStatus, setAoStatus]     = useState<AOStatus | null>(null);
  const [syncing,  setSyncing]      = useState(false);

  // Fetch Angel One status once on mount — lightweight, no polling
  useEffect(() => {
    fetch("/api/integrations/angelone/status")
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setAoStatus(d))
      .catch(() => {}); // silent — status is non-critical
  }, []);

  // Close mobile menu on route change
  useEffect(() => { setMenuOpen(false); }, [pathname]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  async function handleSync() {
    setSyncing(true);
    try {
      const res  = await fetch("/api/integrations/angelone/sync", { method: "POST" });
      const data = await res.json();
      if (data.status === "synced") {
        setAoStatus(prev => prev ? { ...prev, connected: true, last_sync: new Date().toISOString() } : prev);
      }
    } catch {}
    finally { setSyncing(false); }
  }

  // Derive Angel One display state
  const aoConnected = aoStatus?.credentials_configured && aoStatus?.connected;
  const aoLabel     = syncing ? "Syncing…" : aoConnected ? "AngelOne" : "AngelOne";
  const dotClass    = syncing ? "status-dot status-dot-warning" :
                      aoConnected ? "status-dot status-dot-live" :
                      "status-dot status-dot-offline";

  return (
    <>
      <div className="container nav-inner">
        {/* Wordmark */}
        <Link href="/" className="nav-wordmark">WealthOS</Link>

        {/* Desktop links */}
        <nav className="nav-links-desktop" aria-label="Primary navigation">
          {NAV_LINKS.map(({ name, href }) => (
            <Link
              key={href}
              href={href}
              className={`nav-link${pathname === href ? " active" : ""}`}
            >
              {name}
            </Link>
          ))}
        </nav>

        {/* Desktop actions */}
        <div className="nav-actions-desktop">
          {/* Angel One status — dot + text, clickable to sync */}
          <button
            className="ao-status"
            onClick={handleSync}
            disabled={syncing}
            title={aoConnected ? "Click to sync AngelOne" : "AngelOne not connected"}
          >
            <span className={dotClass} aria-hidden="true" />
            <span className="ao-label">{aoLabel}</span>
          </button>

          <button className="btn btn-secondary" onClick={() => setModalOpen(true)}>
            Import Data
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="nav-hamburger btn-icon"
          onClick={() => setMenuOpen(v => !v)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          {/* Three-line icon — pure CSS, no library */}
          <span className={`hamburger-icon${menuOpen ? " open" : ""}`} aria-hidden="true" />
        </button>
      </div>

      {/* Mobile overlay menu */}
      {menuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMenuOpen(false)}>
          <nav
            className="mobile-menu"
            onClick={e => e.stopPropagation()}
            aria-label="Mobile navigation"
          >
            <div className="mobile-menu-header">
              <span className="nav-wordmark">WealthOS</span>
              <button
                className="btn-icon"
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>

            <div className="mobile-menu-links">
              {NAV_LINKS.map(({ name, href }) => (
                <Link
                  key={href}
                  href={href}
                  className={`mobile-nav-link${pathname === href ? " active" : ""}`}
                >
                  {name}
                </Link>
              ))}
            </div>

            <div className="mobile-menu-footer">
              <button className="ao-status" onClick={handleSync} disabled={syncing}>
                <span className={dotClass} aria-hidden="true" />
                <span className="ao-label">{aoLabel}</span>
              </button>
              <button className="btn btn-secondary" style={{ width: "100%" }} onClick={() => { setMenuOpen(false); setModalOpen(true); }}>
                Import Data
              </button>
            </div>
          </nav>
        </div>
      )}

      <ConnectDataModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}
