"use client";
import { useState, useEffect } from 'react';
import './ConnectDataModal.css';

interface ConnectDataModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ConnectDataModal({ isOpen, onClose }: ConnectDataModalProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{status: 'success' | 'error' | null, message: string}>({ status: null, message: '' });

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [parserType, setParserType] = useState<string>('generic');
  const [uploading, setUploading] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [accountId, setAccountId] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      fetch('/api/accounts')
        .then(res => res.json())
        .then(data => {
          setAccounts(data);
          if (data.length > 0 && !accountId) {
            setAccountId(data[0].id.toString());
          }
        })
        .catch(console.error);
    }
  }, [isOpen]);

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
        const errorMsg = Array.isArray(data.detail) ? data.detail.map((d: any) => d.msg).join(', ') : (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail) || 'Failed to sync data');
        setSyncResult({ status: 'error', message: errorMsg });
      }
    } catch (err: any) {
      setSyncResult({ status: 'error', message: err.message || 'Network error occurred' });
    } finally {
      setSyncing(false);
    }
  };

  const handleCsvUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;

    setUploading(true);
    setSyncResult({ status: null, message: '' });

    const formData = new FormData();
    formData.append('file', csvFile);

    try {
      const res = await fetch(`/api/import/csv?account_id=${accountId}`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setSyncResult({ 
          status: 'success', 
          message: `Successfully imported ${data.transactions_imported} transactions.` 
        });
        setTimeout(() => window.location.reload(), 2000);
      } else {
        const errorMsg = Array.isArray(data.detail) ? data.detail.map((d: any) => d.msg).join(', ') : (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail) || 'Failed to import CSV');
        setSyncResult({ status: 'error', message: errorMsg });
      }
    } catch (err: any) {
      setSyncResult({ status: 'error', message: err.message || 'Upload failed' });
    } finally {
      setUploading(false);
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
          
          <hr style={{ borderColor: 'var(--border-color)', margin: '1rem 0' }} />

          {/* CSV Upload Section */}
          <div>
            <h3 className="heading-4" style={{ marginBottom: '1rem' }}>Upload Bank Statement (CSV)</h3>
            <form onSubmit={handleCsvUpload} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                  <label className="type-body-sm text-secondary">Bank / Format</label>
                  <select 
                    value={parserType}
                    onChange={e => setParserType(e.target.value)}
                    style={{ padding: '0.5rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  >
                    <option value="generic">Generic CSV</option>
                    <option value="hdfc">HDFC Bank</option>
                    <option value="icici">ICICI Bank</option>
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                  <label className="type-body-sm text-secondary">Account</label>
                  <select 
                    value={accountId}
                    onChange={e => setAccountId(e.target.value)}
                    required
                    style={{ padding: '0.5rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  >
                    <option value="" disabled>Select Account</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 2 }}>
                  <label className="type-body-sm text-secondary">CSV File</label>
                  <input 
                    type="file" 
                    accept=".csv"
                    onChange={e => setCsvFile(e.target.files ? e.target.files[0] : null)}
                    required
                    style={{ padding: '0.5rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  />
                </div>
              </div>
              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={uploading || !csvFile || !accountId}
              >
                {uploading ? 'Uploading...' : 'Upload CSV'}
              </button>
              {accounts.length === 0 && (
                <p className="text-secondary" style={{ fontSize: '0.8rem', marginTop: '-0.5rem' }}>
                  No accounts found. Please create an account in "Add Manual Data" first.
                </p>
              )}
            </form>
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
