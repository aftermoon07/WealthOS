"use client";
import { useEffect, useState, useMemo } from "react";
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
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<"ALL" | "INCOME" | "EXPENSE">("ALL");

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    try {
      const res = await fetch("/api/transactions?limit=500");
      const data = await res.json();
      setTransactions(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    return transactions.filter(t => {
      const matchType = filterType === "ALL" || t.transaction_type === filterType;
      const q = search.toLowerCase();
      const matchSearch = !q ||
        t.description.toLowerCase().includes(q) ||
        (t.category_name || "").toLowerCase().includes(q) ||
        t.amount.includes(q);
      return matchType && matchSearch;
    });
  }, [transactions, search, filterType]);

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
        fetchTransactions();
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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
        <h1 className="heading-1">All Transactions</h1>
        <span className="text-secondary" style={{ fontSize: "0.85rem" }}>
          Showing {filtered.length} of {transactions.length}
        </span>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search by description, category, or amount..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="edit-input"
          style={{ flex: 1, minWidth: "220px", padding: "0.6rem 1rem" }}
        />
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {(["ALL", "INCOME", "EXPENSE"] as const).map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className="btn-small"
              style={{
                padding: "0.5rem 1rem",
                background: filterType === type ? "var(--brand-primary)" : "var(--bg-secondary)",
                color: filterType === type ? "#fff" : "var(--text-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

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
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "3rem", color: "var(--text-secondary)" }}>
                  No transactions match your search.
                </td>
              </tr>
            ) : (
              filtered.map(txn => {
                const isEditing = editingId === txn.id;
                return (
                  <tr key={txn.id} className="txn-row">
                    <td>
                      {isEditing ? (
                        <input type="date" className="edit-input" value={editForm.date}
                          onChange={e => setEditForm({...editForm, date: e.target.value})} />
                      ) : txn.date}
                    </td>
                    <td>
                      {isEditing ? (
                        <input type="text" className="edit-input" value={editForm.description}
                          onChange={e => setEditForm({...editForm, description: e.target.value})} />
                      ) : txn.description}
                    </td>
                    <td>{txn.category_name || "Uncategorized"}</td>
                    <td>
                      {isEditing ? (
                        <input type="number" className="edit-input" step="0.01" value={editForm.amount}
                          onChange={e => setEditForm({...editForm, amount: String(e.target.value)})} />
                      ) : parseFloat(txn.amount).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                    </td>
                    <td>
                      {isEditing ? (
                        <select className="edit-input" value={editForm.transaction_type}
                          onChange={e => setEditForm({...editForm, transaction_type: e.target.value})}>
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
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
