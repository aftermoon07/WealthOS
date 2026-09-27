"use client";
import { useEffect, useState } from "react";
import "./Transactions.css";

type Transaction = {
  id: number;
  date: string;
  amount: string;
  description: string;
  transaction_type: string;
  category_name?: string;
  account_id: number;
};

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<Transaction>>({});

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    try {
      const res = await fetch("/api/transactions?limit=200");
      const data = await res.json();
      setTransactions(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this transaction?")) return;
    try {
      const res = await fetch(`/api/transactions/${id}`, { method: "DELETE" });
      if (res.ok) {
        setTransactions(transactions.filter(t => t.id !== id));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleEditClick = (txn: Transaction) => {
    setEditingId(txn.id);
    setEditForm(txn);
  };

  const handleSave = async (id: number) => {
    try {
      const res = await fetch(`/api/transactions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: parseFloat(String(editForm.amount)),
          description: editForm.description,
          date: editForm.date,
          transaction_type: editForm.transaction_type,
        }),
      });
      if (res.ok) {
        setEditingId(null);
        fetchTransactions(); // refresh
      } else {
        const err = await res.json();
        alert("Error saving: " + JSON.stringify(err));
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) return <div className="container" style={{ padding: "4rem 0" }}>Loading...</div>;

  return (
    <div className="container transactions-page">
      <h1 className="heading-1" style={{ marginBottom: "1.5rem" }}>All Transactions</h1>
      
      <div className="glass-card table-container">
        <table className="txn-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Amount (₹)</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map(txn => {
              const isEditing = editingId === txn.id;
              
              return (
                <tr key={txn.id} className="txn-row">
                  <td>
                    {isEditing ? (
                      <input 
                        type="date" 
                        className="edit-input"
                        value={editForm.date} 
                        onChange={e => setEditForm({...editForm, date: e.target.value})}
                      />
                    ) : (
                      txn.date
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <input 
                        type="text" 
                        className="edit-input"
                        value={editForm.description} 
                        onChange={e => setEditForm({...editForm, description: e.target.value})}
                      />
                    ) : (
                      txn.description
                    )}
                  </td>
                  <td>{txn.category_name || "Uncategorized"}</td>
                  <td>
                    {isEditing ? (
                      <input 
                        type="number" 
                        className="edit-input"
                        step="0.01"
                        value={editForm.amount} 
                        onChange={e => setEditForm({...editForm, amount: String(e.target.value)})}
                      />
                    ) : (
                      parseFloat(txn.amount).toLocaleString("en-IN", { maximumFractionDigits: 2 })
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <select 
                        className="edit-input"
                        value={editForm.transaction_type}
                        onChange={e => setEditForm({...editForm, transaction_type: e.target.value})}
                      >
                        <option value="EXPENSE">EXPENSE</option>
                        <option value="INCOME">INCOME</option>
                      </select>
                    ) : (
                      <span className={`badge ${txn.transaction_type.toLowerCase()}`}>
                        {txn.transaction_type}
                      </span>
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <div className="actions">
                        <button className="btn-small btn-edit" onClick={() => handleSave(txn.id)}>Save</button>
                        <button className="btn-small" style={{ background: "var(--bg-secondary)", color: "var(--text-primary)" }} onClick={() => setEditingId(null)}>Cancel</button>
                      </div>
                    ) : (
                      <div className="actions">
                        <button className="btn-small btn-edit" onClick={() => handleEditClick(txn)}>Edit</button>
                        <button className="btn-small btn-delete" onClick={() => handleDelete(txn.id)}>Delete</button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
