"use client";
import { useState } from 'react';
import './ConnectDataModal.css';

interface ConnectDataModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ConnectDataModal({ isOpen, onClose }: ConnectDataModalProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{status: 'success' | 'error' | null, message: string}>({ status: null, message: '' });

  if (!isOpen) return null;

  const handleSyncAngelOne = async () => {
    setSyncing(true);
    setSyncResult({ status: null, message: '' });
    
    try {
      const res = await fetch('http://localhost:8000/api/integrations/angelone/sync', {
        method: 'POST',
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setSyncResult({ 
          status: 'success', 
          message: `Successfully synced ${data.holdings_synced || 0} holdings and ${data.trades_synced || 0} trades.` 
        });
        
        // Optionally refresh page after short delay to show new data
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        setSyncResult({ status: 'error', message: data.detail || 'Failed to sync data' });
      }
    } catch (err: any) {
      setSyncResult({ status: 'error', message: err.message || 'Network error occurred' });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="heading-3">Connect Data Sources</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        
        <p className="text-secondary modal-desc">
          Connect your brokerage and bank accounts to stream live financial data into the Intelligence Engine.
        </p>

        <div className="integration-list">
          {/* Angel One Integration */}
          <div className="integration-item connected">
            <div className="integration-info">
              <div className="integration-icon angel-one">AO</div>
              <div>
                <h3 className="integration-name">Angel One</h3>
                <p className="integration-status text-success">Connected via SmartAPI</p>
              </div>
            </div>
            <button 
              className={`btn ${syncing ? 'btn-secondary' : 'btn-primary'}`} 
              onClick={handleSyncAngelOne}
              disabled={syncing}
            >
              {syncing ? 'Syncing...' : 'Sync Live Data'}
            </button>
          </div>

          {/* Plaid - Coming Soon */}
          <div className="integration-item disabled">
            <div className="integration-info">
              <div className="integration-icon plaid">P</div>
              <div>
                <h3 className="integration-name">Plaid</h3>
                <p className="integration-status text-secondary">Bank Accounts & Cards (Coming Soon)</p>
              </div>
            </div>
            <button className="btn btn-secondary" disabled>Connect</button>
          </div>

          {/* Coinbase - Coming Soon */}
          <div className="integration-item disabled">
            <div className="integration-info">
              <div className="integration-icon coinbase">C</div>
              <div>
                <h3 className="integration-name">Coinbase</h3>
                <p className="integration-status text-secondary">Crypto Wallets (Coming Soon)</p>
              </div>
            </div>
            <button className="btn btn-secondary" disabled>Connect</button>
          </div>
        </div>

        {syncResult.status && (
          <div className={`sync-alert alert-${syncResult.status}`}>
            {syncResult.status === 'success' ? '✅ ' : '❌ '}
            {syncResult.message}
          </div>
        )}
      </div>
    </div>
  );
}
