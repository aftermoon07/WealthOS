"use client";
import { useState, useEffect } from 'react';
import './ConnectDataModal.css';

interface AddTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AddTransactionModal({ isOpen, onClose }: AddTransactionModalProps) {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{status: 'success' | 'error' | null, message: string}>({ status: null, message: '' });
  
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    account_id: '',
    amount: '',
    description: '',
    transaction_type: 'EXPENSE'
  });

  useEffect(() => {
    if (isOpen) {
      fetch('/api/accounts')
        .then(res => res.json())
        .then(data => {
          setAccounts(data);
          if (data.length > 0 && !formData.account_id) {
            setFormData(prev => ({ ...prev, account_id: data[0].id.toString() }));
          }
        })
        .catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult({ status: null, message: '' });

    try {
      const res = await fetch('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: formData.date,
          account_id: parseInt(formData.account_id),
          amount: parseFloat(formData.amount),
          description: formData.description,
          transaction_type: formData.transaction_type,
          currency: 'INR'
        })
      });

      const data = await res.json();
      if (res.ok) {
        setResult({ status: 'success', message: 'Transaction added successfully!' });
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        setResult({ status: 'error', message: data.detail || 'Failed to add transaction' });
      }
    } catch (err: any) {
      setResult({ status: 'error', message: err.message || 'Network error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="heading-3">Add Manual Transaction</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        
        <p className="text-secondary modal-desc" style={{ marginBottom: '1.5rem' }}>
          Manually enter an income or expense transaction.
        </p>
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
              <label className="type-body-sm text-secondary">Type</label>
              <select 
                value={formData.transaction_type}
                onChange={e => setFormData({...formData, transaction_type: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
              >
                <option value="EXPENSE">Expense</option>
                <option value="INCOME">Income</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
              <label className="type-body-sm text-secondary">Date</label>
              <input 
                type="date" 
                required
                value={formData.date}
                onChange={e => setFormData({...formData, date: e.target.value})}
                style={{ padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label className="type-body-sm text-secondary">Account</label>
            <select 
              value={formData.account_id}
              onChange={e => setFormData({...formData, account_id: e.target.value})}
              required
              style={{ padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            >
              <option value="" disabled>Select Account</option>
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>{acc.name} ({acc.account_type})</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label className="type-body-sm text-secondary">Amount (₹)</label>
            <input 
              type="number" 
              step="0.01" 
              required
              min="0.01"
              value={formData.amount}
              onChange={e => setFormData({...formData, amount: e.target.value})}
              placeholder="e.g. 500"
              style={{ padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label className="type-body-sm text-secondary">Description</label>
            <input 
              type="text" 
              required
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              placeholder="e.g. Grocery shopping"
              style={{ padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ marginTop: '1rem', width: '100%' }}
            disabled={loading}
          >
            {loading ? 'Adding...' : 'Add Transaction'}
          </button>
        </form>

        {result.status && (
          <div className={`sync-alert alert-${result.status}`} style={{ marginTop: '1rem' }}>
            {result.status === 'success' ? '✅ ' : '❌ '}
            {result.message}
          </div>
        )}
      </div>
    </div>
  );
}
