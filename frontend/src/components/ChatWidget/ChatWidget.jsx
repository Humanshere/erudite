import React, { useState } from "react";
import client from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import "./ChatWidget.css";

function buildTableResult(data) {
  const columns = Array.isArray(data?.columns) ? data.columns : [];
  const rows = Array.isArray(data?.rows) ? data.rows : [];

  if (rows.length && !columns.length && rows[0] && typeof rows[0] === "object" && !Array.isArray(rows[0])) {
    const inferredColumns = Object.keys(rows[0]);

    return {
      columns: inferredColumns,
      rows: rows.map((row) => inferredColumns.map((key) => row?.[key])),
    };
  }

  return { columns, rows };
}

export default function ChatWidget({ open, onClose }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endOfMessagesRef = React.useRef(null);

  React.useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = { from: "user", text: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await client.post("/chatbot/query/", { prompt: input });
      const table = buildTableResult(res.data);
      setMessages((m) => [...m, { from: "bot", kind: "table", table }]);
    } catch (err) {
      const backendError = err?.response?.data?.error;
      const backendDetail = err?.response?.data?.detail;
      const msg = backendDetail ? `${backendError || "Error"}: ${backendDetail}` : (backendError || err.message);
      setMessages((m) => [...m, { from: "bot", kind: "error", text: "Error: " + msg }]);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="chat-overlay" onClick={onClose}>
      <div className="chat-panel" onClick={(e) => e.stopPropagation()}>
        <div className="chat-header">
          <strong>DB Chat ({user?.role})</strong>
          <button onClick={onClose}>Close</button>
        </div>
        <div className="chat-body">
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.from}`}>
              {m.kind === "table" ? (
                <div className="chat-table-wrap">
                  {m.table.columns.length ? (
                    <table className="chat-table">
                      <thead>
                        <tr>
                          {m.table.columns.map((column) => (
                            <th key={column}>{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {m.table.rows.length ? (
                          m.table.rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              {m.table.columns.map((_, columnIndex) => (
                                <td key={columnIndex}>{String(row?.[columnIndex] ?? "")}</td>
                              ))}
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td className="chat-table-empty" colSpan={m.table.columns.length}>
                              No rows returned.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  ) : (
                    <div className="chat-table-empty">No tabular data returned.</div>
                  )}
                </div>
              ) : (
                m.text
              )}
            </div>
          ))}
          <div ref={endOfMessagesRef} />
        </div>
        <div className="chat-footer">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about the database..." />
          <button onClick={send} disabled={loading}>{loading ? "…" : "Send"}</button>
        </div>
      </div>
    </div>
  );
}
