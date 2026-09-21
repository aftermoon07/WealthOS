"use client";
import { useState, useRef, useEffect } from "react";
import "./Assistant.css";

type Message = {
  role: "user" | "assistant";
  content: string;
  confidence?: string;
  evidence?: string[];
  drivers?: string[];
  watch_items?: string[];
  tools_called?: string[];
  error?: string | null;
};

const SUGGESTIONS = [
  "What is my XIRR and how is my portfolio performing?",
  "Where am I spending the most this month?",
  "Am I saving enough to meet my goals?",
  "Are there any unusual transactions I should know about?",
  "What is my current net worth?",
  "How diversified is my portfolio?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm your WealthOS AI Assistant. I have access to your complete financial data — portfolio, spending, cash flow, and goals. Ask me anything about your money.",
      confidence: "HIGH",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text?: string) {
    const question = text || input.trim();
    if (!question || loading) return;

    const userMsg: Message = { role: "user", content: question };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });
      const data = await res.json();

      const assistantMsg: Message = {
        role: "assistant",
        content: data.summary || "I was unable to generate a response.",
        confidence: data.confidence,
        evidence: data.evidence || [],
        drivers: data.drivers || [],
        watch_items: data.watch_items || [],
        tools_called: data.tools_called || [],
        error: data.error,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠ Connection error. Please ensure the backend is running.",
        confidence: "LOW",
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="container assistant-layout animate-fade-in">
      <div className="flex-row space-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="heading-1 text-gradient">WealthOS AI</h1>
          <p className="text-body">Powered by Gemini + grounded in your real financial data.</p>
        </div>
      </div>

      <div className="chat-container glass-panel">
        {/* Messages */}
        <div className="messages-area">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.role === "assistant" && (
                <div className="assistant-avatar">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#ag)"/>
                    <defs>
                      <linearGradient id="ag" x1="2" y1="7" x2="22" y2="7">
                        <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
              )}

              <div className="message-body">
                <div className="message-content">{msg.content}</div>

                {msg.role === "assistant" && msg.confidence && (
                  <div className="message-meta">
                    <span className={`badge ${
                      msg.confidence === "HIGH" ? "badge-success" :
                      msg.confidence === "MEDIUM" ? "badge-warning" : "badge-danger"
                    }`}>
                      {msg.confidence} confidence
                    </span>
                    {msg.tools_called && msg.tools_called.length > 0 && (
                      <span className="text-small" style={{ marginLeft: "0.75rem" }}>
                        Tools: {msg.tools_called.join(", ")}
                      </span>
                    )}
                  </div>
                )}

                {msg.evidence && msg.evidence.length > 0 && (
                  <div className="evidence-panel">
                    <strong className="text-small" style={{ color: "var(--accent-primary)", display: "block", marginBottom: "0.5rem" }}>
                      📊 Evidence
                    </strong>
                    {msg.evidence.map((e, j) => (
                      <div key={j} className="evidence-item text-small">{e}</div>
                    ))}
                  </div>
                )}

                {msg.watch_items && msg.watch_items.length > 0 && (
                  <div className="watch-panel">
                    <strong className="text-small" style={{ color: "var(--warning)", display: "block", marginBottom: "0.5rem" }}>
                      ⚠ Watch Items
                    </strong>
                    {msg.watch_items.map((w, j) => (
                      <div key={j} className="text-small" style={{ marginBottom: "0.25rem" }}>• {w}</div>
                    ))}
                  </div>
                )}

                {msg.error && (
                  <div className="error-note text-small">⚠ {msg.error}</div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="assistant-avatar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#ag2)"/>
                  <defs>
                    <linearGradient id="ag2" x1="2" y1="7" x2="22" y2="7">
                      <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div className="message-body">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length <= 1 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button key={i} className="suggestion-chip" onClick={() => sendMessage(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="input-area">
          <textarea
            id="assistant-input"
            className="chat-input"
            placeholder="Ask about your finances... (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={loading}
          />
          <button
            id="assistant-send-btn"
            className="btn btn-primary send-btn"
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
          >
            {loading ? "..." : "→"}
          </button>
        </div>
      </div>
    </div>
  );
}
