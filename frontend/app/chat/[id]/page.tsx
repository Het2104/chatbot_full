"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { startChat, sendMessage, getParentFAQs } from "../../../services/api";
import PdfUploadButton from "../../../components/PdfUploadButton";
import UrlIngestButton from "../../../components/UrlIngestButton";

type Message = {
  sender: "user" | "bot";
  text: string;
  options?: NodeOption[];
};

type NodeOption = {
  id?: number;
  text: string;
};

type TriggerNode = {
  id: number;
  text: string;
  workflow_id: number;
};

type FAQ = {
  id: number;
  chatbot_id: number;
  question: string;
  answer: string;
  is_active: boolean;
  display_order: number;
  created_at: string;
};

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const chatbotId = params.id as string;

  const [sessionId, setSessionId] = useState<string | number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [triggerNodes, setTriggerNodes] = useState<TriggerNode[]>([]);

  useEffect(() => {
    const initChat = async () => {
      setLoading(true);
      setError(null);
      try {
        const [chatResult, parentFaqsResult] = await Promise.all([
          startChat(chatbotId),
          getParentFAQs(chatbotId),
        ]);
        
        const result = chatResult as { 
          session_id: string | number;
          trigger_nodes: TriggerNode[];
        };
        setSessionId(result.session_id);
        setTriggerNodes(result.trigger_nodes || []);
        
        const parentFaqsData = parentFaqsResult as FAQ[];
        setFaqs(Array.isArray(parentFaqsData) ? parentFaqsData : []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start chat");
      } finally {
        setLoading(false);
      }
    };

    initChat();
  }, [chatbotId]);

  const handleSend = async () => {
    if (!input.trim() || !sessionId) {
      return;
    }

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userMessage }]);

    await sendAndAppendBotReply(userMessage);
  };

  const handleOptionClick = async (text: string) => {
    if (!sessionId) return;

    setMessages((prev) => [...prev, { sender: "user", text }]);
    await sendAndAppendBotReply(text);
  };

  const sendAndAppendBotReply = async (messageText: string) => {
    if (!sessionId) return;

    setSending(true);
    setError(null);
    try {
      const response = await sendMessage(sessionId, messageText);
      
      // Log response for debugging
      console.log('API Response:', response);
      
      // Extract bot_response - handle both direct response and nested .data structure
      const botReply = (response as any)?.bot_response || (response as any)?.data?.bot_response || '';
      const options = (response as any)?.options || (response as any)?.data?.options || [];
      
      console.log('Bot Reply:', botReply);
      console.log('Options:', options);
      
      // Ensure we have valid text
      if (!botReply && botReply !== '') {
        console.error('No bot_response found in response:', response);
        throw new Error('Invalid response structure - missing bot_response field');
      }

      // Update messages state with bot response
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: botReply, options: options.length > 0 ? options : undefined },
      ]);
      
      console.log('Messages updated successfully');
    } catch (err) {
      console.error('Error in sendAndAppendBotReply:', err);
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: 24 }}>
      <button
        onClick={() => router.back()}
        style={{ marginBottom: 16, padding: 8 }}
      >
        ← Back
      </button>

      <h1>Chat with Chatbot {chatbotId}</h1>

      {loading && <p>Starting chat...</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: 6,
          padding: 12,
          height: 400,
          overflowY: "auto",
          marginBottom: 16,
          backgroundColor: "#f9f9f9",
        }}
      >
        {messages.length === 0 ? (
          <p style={{ color: "#999" }}>No messages yet. Start chatting!</p>
        ) : (
          <div>
            {messages.map((msg, idx) => (
              <div key={idx} style={{ marginBottom: 12 }}>
                <div
                  style={{
                    padding: 8,
                    borderRadius: 4,
                    backgroundColor: msg.sender === "user" ? "#e3f2fd" : "#fff",
                    borderLeft: `4px solid ${
                      msg.sender === "user" ? "#2196F3" : "#4CAF50"
                    }`,
                  }}
                >
                  <strong>{msg.sender === "user" ? "You" : "Bot"}:</strong>
                  <p style={{ margin: "4px 0 0" }}>{msg.text}</p>
                </div>
                
                {/* Render contextual options below bot messages */}
                {msg.sender === "bot" && msg.options && msg.options.length > 0 && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: 10,
                      backgroundColor: "#fffde7",
                      border: "1px solid #fbc02d",
                      borderRadius: 4,
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    {msg.options.map((option, optIdx) => (
                      <button
                        key={optIdx}
                        onClick={() => handleOptionClick(option.text)}
                        disabled={sending || !sessionId}
                        style={{
                          padding: "6px 12px",
                          backgroundColor: "#fbc02d",
                          border: "1px solid #f57f17",
                          borderRadius: 16,
                          cursor: sending || !sessionId ? "not-allowed" : "pointer",
                          fontSize: 13,
                          color: "#f57f17",
                          fontWeight: 500,
                          opacity: sending || !sessionId ? 0.6 : 1,
                        }}
                      >
                        {option.text}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Trigger Nodes Section (Workflow Entry Points) */}
      {triggerNodes.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8, color: "#666" }}>
            Choose a topic:
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {triggerNodes.map((trigger) => (
              <button
                key={trigger.id}
                onClick={() => handleOptionClick(trigger.text)}
                disabled={sending || !sessionId}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#7c4dff",
                  border: "none",
                  borderRadius: 20,
                  cursor: sending || !sessionId ? "not-allowed" : "pointer",
                  fontSize: 14,
                  color: "#fff",
                  fontWeight: 600,
                  opacity: sending || !sessionId ? 0.6 : 1,
                  boxShadow: "0 2px 4px rgba(124, 77, 255, 0.3)",
                }}
              >
                {trigger.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* FAQ Section */}
      {faqs.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8, color: "#666" }}>
            Frequently Asked Questions:
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {faqs.map((faq) => (
              <button
                key={faq.id}
                onClick={() => handleOptionClick(faq.question)}
                disabled={sending || !sessionId}
                style={{
                  padding: "6px 12px",
                  backgroundColor: "#e3f2fd",
                  border: "1px solid #2196F3",
                  borderRadius: 16,
                  cursor: sending || !sessionId ? "not-allowed" : "pointer",
                  fontSize: 13,
                  color: "#1976d2",
                  opacity: sending || !sessionId ? 0.6 : 1,
                }}
              >
                {faq.question}
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <PdfUploadButton
          onUploadSuccess={(filename, numChunks) => {
            console.log(`Uploaded ${filename} with ${numChunks} chunks`);
          }}
          onUploadError={(error) => {
            console.error("Upload error:", error);
          }}
        />
        <UrlIngestButton
          onIngestSuccess={(url, numChunks) => {
            console.log(`Indexed ${url} with ${numChunks} chunks`);
          }}
          onIngestError={(error) => {
            console.error("URL ingest error:", error);
          }}
        />
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyPress={(event) => {
            if (event.key === "Enter" && !sending) {
              handleSend();
            }
          }}
          placeholder="Type message..."
          disabled={!sessionId || sending}
          style={{ flex: 1, padding: 8 }}
        />
        <button
          onClick={handleSend}
          disabled={!sessionId || !input.trim() || sending}
          style={{ padding: 8 }}
        >
          {sending ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
