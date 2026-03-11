"use client";

/**
 * Embed Chat Page
 *
 * Minimal chat UI intended to be loaded inside an <iframe> on third-party websites.
 * There is no NavBar, no auth guard, no upload buttons.
 *
 * Flow:
 *  1. Fetch /public/chatbot/{embedKey} → get chatbot_id + widget settings
 *  2. startChat(chatbot_id) + getParentFAQs(chatbot_id) in parallel
 *  3. Show widget_welcome_message as first bot message
 *  4. Normal chat loop: sendMessage/queue + WebSocket
 */

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { startChat, sendMessage, getParentFAQs } from "../../../services/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Message = {
  sender: "user" | "bot";
  text: string;
  options?: { id?: number; text: string }[];
};

type TriggerNode = { id: number; text: string; workflow_id: number };
type FAQ = { id: number; chatbot_id: number; question: string; answer: string; is_active: boolean; display_order: number };

type WidgetConfig = {
  chatbot_id: number;
  name: string;
  widget_color: string;
  widget_welcome_message: string;
  widget_position: string;
};

export default function EmbedChatPage() {
  const params = useParams();
  const embedKey = params.embedKey as string;

  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [sessionId, setSessionId] = useState<string | number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [triggerNodes, setTriggerNodes] = useState<TriggerNode[]>([]);
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // 1. Load widget config + start chat
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch publicly available widget config
        const res = await fetch(`${BASE_URL}/public/chatbot/${embedKey}`);
        if (!res.ok) throw new Error("Widget not found");
        const cfg: WidgetConfig = await res.json();
        setConfig(cfg);

        // In parallel: start session + load parent FAQs
        const [chatResult, faqResult] = await Promise.all([
          startChat(cfg.chatbot_id),
          getParentFAQs(cfg.chatbot_id),
        ]);

        const chat = chatResult as { session_id: string | number; trigger_nodes: TriggerNode[] };
        setSessionId(chat.session_id);
        setTriggerNodes(chat.trigger_nodes || []);
        setFaqs(Array.isArray(faqResult) ? (faqResult as FAQ[]) : []);

        // Show welcome message
        setMessages([{ sender: "bot", text: cfg.widget_welcome_message }]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start chat");
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [embedKey]);

  // 2. Send a message and append bot reply
  const sendAndAppendBotReply = async (text: string) => {
    if (!sessionId) return;
    setSending(true);
    setError(null);
    try {
      const response = await sendMessage(sessionId, text);
      const botReply = (response as any)?.bot_response ?? "";
      const options = (response as any)?.options ?? [];
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: botReply, options: options.length ? options : undefined },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !sessionId || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text }]);
    await sendAndAppendBotReply(text);
  };

  const handleQuickReply = async (text: string) => {
    if (!sessionId || sending) return;
    setMessages((prev) => [...prev, { sender: "user", text }]);
    await sendAndAppendBotReply(text);
  };

  const color = config?.widget_color ?? "#2563EB";

  /* ------------------------------------------------------------------ */
  /* Render                                                               */
  /* ------------------------------------------------------------------ */
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        fontFamily: "system-ui, -apple-system, sans-serif",
        backgroundColor: "#f8fafc",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          backgroundColor: color,
          color: "#fff",
          padding: "12px 16px",
          fontWeight: 700,
          fontSize: 15,
          flexShrink: 0,
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        }}
      >
        {config?.name ?? "Chat"}
      </div>

      {/* Messages area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 12px 6px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        {loading && (
          <p style={{ color: "#94a3b8", textAlign: "center", marginTop: 32 }}>
            Starting chat…
          </p>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "82%",
                padding: "8px 12px",
                borderRadius: msg.sender === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                backgroundColor: msg.sender === "user" ? color : "#fff",
                color: msg.sender === "user" ? "#fff" : "#1e293b",
                fontSize: 14,
                lineHeight: 1.45,
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                wordBreak: "break-word",
              }}
            >
              {msg.text}
            </div>

            {/* Quick-reply options below bot messages */}
            {msg.sender === "bot" && msg.options && msg.options.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                {msg.options.map((opt, oi) => (
                  <button
                    key={oi}
                    onClick={() => handleQuickReply(opt.text)}
                    disabled={sending}
                    style={{
                      padding: "5px 12px",
                      border: `1.5px solid ${color}`,
                      borderRadius: 16,
                      background: "#fff",
                      color: color,
                      fontSize: 13,
                      cursor: sending ? "not-allowed" : "pointer",
                      opacity: sending ? 0.6 : 1,
                      fontWeight: 500,
                    }}
                  >
                    {opt.text}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {sending && (
          <div style={{ display: "flex", alignItems: "flex-start" }}>
            <div
              style={{
                padding: "8px 14px",
                borderRadius: "16px 16px 16px 4px",
                backgroundColor: "#fff",
                fontSize: 14,
                color: "#94a3b8",
                boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
              }}
            >
              Typing…
            </div>
          </div>
        )}

        {error && (
          <p style={{ color: "#ef4444", fontSize: 13, textAlign: "center" }}>{error}</p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Trigger-node quick-starts */}
      {!loading && triggerNodes.length > 0 && (
        <div
          style={{
            padding: "6px 12px",
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            flexShrink: 0,
            borderTop: "1px solid #e2e8f0",
            backgroundColor: "#fff",
          }}
        >
          {triggerNodes.map((t) => (
            <button
              key={t.id}
              onClick={() => handleQuickReply(t.text)}
              disabled={sending}
              style={{
                padding: "5px 12px",
                background: color,
                color: "#fff",
                border: "none",
                borderRadius: 14,
                fontSize: 13,
                cursor: sending ? "not-allowed" : "pointer",
                opacity: sending ? 0.6 : 1,
                fontWeight: 600,
              }}
            >
              {t.text}
            </button>
          ))}
        </div>
      )}

      {/* FAQ quick-starts */}
      {!loading && faqs.length > 0 && (
        <div
          style={{
            padding: "6px 12px",
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            flexShrink: 0,
            backgroundColor: "#f0f7ff",
            borderTop: "1px solid #bfdbfe",
          }}
        >
          {faqs.slice(0, 5).map((faq) => (
            <button
              key={faq.id}
              onClick={() => handleQuickReply(faq.question)}
              disabled={sending}
              style={{
                padding: "5px 12px",
                background: "#fff",
                color: "#2563eb",
                border: "1px solid #93c5fd",
                borderRadius: 14,
                fontSize: 12,
                cursor: sending ? "not-allowed" : "pointer",
                opacity: sending ? 0.6 : 1,
              }}
            >
              {faq.question}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "10px 12px",
          borderTop: "1px solid #e2e8f0",
          backgroundColor: "#fff",
          flexShrink: 0,
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type a message…"
          disabled={loading || sending || !sessionId}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: 20,
            border: "1.5px solid #e2e8f0",
            fontSize: 14,
            outline: "none",
            backgroundColor: "#f8fafc",
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || sending || !sessionId || !input.trim()}
          style={{
            padding: "8px 16px",
            backgroundColor: color,
            color: "#fff",
            border: "none",
            borderRadius: 20,
            fontSize: 14,
            fontWeight: 600,
            cursor: loading || sending || !input.trim() ? "not-allowed" : "pointer",
            opacity: loading || sending || !input.trim() ? 0.6 : 1,
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
