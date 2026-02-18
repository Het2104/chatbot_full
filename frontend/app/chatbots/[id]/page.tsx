"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getWorkflows,
  createWorkflow,
  activateWorkflow,
  deleteWorkflow,
  getFAQs,
  createFAQ,
  updateFAQ,
  deleteFAQ,
} from "../../../services/api";

type Workflow = {
  id: string | number;
  name?: string;
  is_active?: boolean;
};

type FAQ = {
  id: number;
  chatbot_id: number;
  question: string;
  answer: string;
  parent_id?: number | null;
  is_active: boolean;
  display_order: number;
  created_at: string;
};

export default function ChatbotPage() {
  const params = useParams();
  const router = useRouter();
  const chatbotId = params.id as string;

  const [activeTab, setActiveTab] = useState<"workflows" | "faqs">("workflows");
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [faqs, setFAQs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // FAQ form state
  const [faqQuestion, setFaqQuestion] = useState("");
  const [faqAnswer, setFaqAnswer] = useState("");
  const [faqParentId, setFaqParentId] = useState<string>("");
  const [faqSubmitting, setFaqSubmitting] = useState(false);

  const parentQuestionById = faqs.reduce<Record<number, string>>((acc, faq) => {
    acc[faq.id] = faq.question;
    return acc;
  }, {});

  const loadWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await getWorkflows(chatbotId)) as Workflow[];
      setWorkflows(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  };

  const loadFAQs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await getFAQs(chatbotId)) as FAQ[];
      setFAQs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load FAQs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "workflows") {
      loadWorkflows();
    } else {
      loadFAQs();
    }
  }, [chatbotId, activeTab]);

  const handleCreateWorkflow = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Workflow name is required");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await createWorkflow(chatbotId, { name: name.trim() });
      setName("");
      await loadWorkflows();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create workflow"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleActivateWorkflow = async (workflowId: string | number) => {
    setError(null);
    try {
      await activateWorkflow(workflowId);
      await loadWorkflows(); // IMPORTANT: refresh UI
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to activate workflow"
      );
    }
  };

  const handleDeleteWorkflow = async (workflowId: string | number) => {
    if (!confirm("Are you sure you want to delete this workflow?")) {
      return;
    }
    setError(null);
    try {
      await deleteWorkflow(workflowId);
      await loadWorkflows();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete workflow"
      );
    }
  };

  const handleCreateFAQ = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!faqQuestion.trim() || !faqAnswer.trim()) {
      setError("Question and answer are required");
      return;
    }

    setFaqSubmitting(true);
    setError(null);
    try {
      const parentIdValue = faqParentId ? Number(faqParentId) : null;
      await createFAQ(chatbotId, {
        question: faqQuestion.trim(),
        answer: faqAnswer.trim(),
        parent_id: parentIdValue,
        is_active: true,
      });
      setFaqQuestion("");
      setFaqAnswer("");
      setFaqParentId("");
      await loadFAQs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create FAQ");
    } finally {
      setFaqSubmitting(false);
    }
  };

  const handleToggleFAQ = async (faq: FAQ) => {
    setError(null);
    try {
      await updateFAQ(faq.id, { is_active: !faq.is_active });
      await loadFAQs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update FAQ");
    }
  };

  const handleDeleteFAQ = async (faqId: number) => {
    if (!confirm("Are you sure you want to delete this FAQ?")) {
      return;
    }
    setError(null);
    try {
      await deleteFAQ(faqId);
      await loadFAQs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete FAQ");
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

      <h1>Chatbot {chatbotId} Settings</h1>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, borderBottom: "2px solid #ddd" }}>
        <button
          onClick={() => setActiveTab("workflows")}
          style={{
            padding: "8px 16px",
            border: "none",
            background: "transparent",
            borderBottom: activeTab === "workflows" ? "2px solid #3b82f6" : "none",
            cursor: "pointer",
            fontWeight: activeTab === "workflows" ? "bold" : "normal",
          }}
        >
          Workflows
        </button>
        <button
          onClick={() => setActiveTab("faqs")}
          style={{
            padding: "8px 16px",
            border: "none",
            background: "transparent",
            borderBottom: activeTab === "faqs" ? "2px solid #3b82f6" : "none",
            cursor: "pointer",
            fontWeight: activeTab === "faqs" ? "bold" : "normal",
          }}
        >
          FAQs
        </button>
      </div>

      {error && <p style={{ color: "crimson", marginBottom: 16 }}>{error}</p>}

      {/* Workflows Tab */}
      {activeTab === "workflows" && (
        <>
          <form onSubmit={handleCreateWorkflow} style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label>
                Workflow Name
                <input
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  style={{ width: "100%", padding: 8, marginTop: 4 }}
                />
              </label>
              <button type="submit" disabled={submitting} style={{ padding: 8 }}>
                {submitting ? "Creating..." : "Create Workflow"}
              </button>
            </div>
          </form>

          {loading && <p>Loading...</p>}

          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {workflows.map((workflow) => (
              <li
                key={workflow.id}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 6,
                  padding: 12,
                  marginBottom: 12,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div
                    onClick={() => router.push(`/workflows/${workflow.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <strong>{workflow.name ?? "Untitled"}</strong>
                    {workflow.is_active && (
                      <span
                        style={{
                          marginLeft: 8,
                          padding: "2px 6px",
                          backgroundColor: "#4CAF50",
                          color: "white",
                          borderRadius: 3,
                          fontSize: 12,
                        }}
                      >
                        Active
                      </span>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: 6 }}>
                    {!workflow.is_active && (
                      <button
                        onClick={() => handleActivateWorkflow(workflow.id)}
                        style={{ padding: "6px 12px" }}
                      >
                        Activate
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteWorkflow(workflow.id)}
                      style={{
                        padding: "6px 12px",
                        backgroundColor: "#f44336",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                        cursor: "pointer",
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* FAQs Tab */}
      {activeTab === "faqs" && (
        <>
          <form onSubmit={handleCreateFAQ} style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <label>
                Parent FAQ (optional)
                <select
                  value={faqParentId}
                  onChange={(e) => setFaqParentId(e.target.value)}
                  style={{ width: "100%", padding: 8, marginTop: 4 }}
                >
                  <option value="">No parent (top-level)</option>
                  {faqs
                    .filter((faq) => faq.parent_id == null)
                    .map((faq) => (
                      <option key={faq.id} value={faq.id}>
                        {faq.question}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Question
                <input
                  type="text"
                  value={faqQuestion}
                  onChange={(e) => setFaqQuestion(e.target.value)}
                  placeholder="What is the question?"
                  style={{ width: "100%", padding: 8, marginTop: 4 }}
                />
              </label>
              <label>
                Answer
                <textarea
                  value={faqAnswer}
                  onChange={(e) => setFaqAnswer(e.target.value)}
                  placeholder="The answer to the question"
                  rows={3}
                  style={{ width: "100%", padding: 8, marginTop: 4 }}
                />
              </label>
              <button type="submit" disabled={faqSubmitting} style={{ padding: 8 }}>
                {faqSubmitting ? "Creating..." : "Add FAQ"}
              </button>
            </div>
          </form>

          {loading && <p>Loading...</p>}

          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {faqs.map((faq) => (
              <li
                key={faq.id}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 6,
                  padding: 12,
                  marginBottom: 12,
                  opacity: faq.is_active ? 1 : 0.5,
                }}
              >
                <div style={{ marginBottom: 8 }}>
                  <strong>Q: {faq.question}</strong>
                  {faq.parent_id != null && (
                    <span
                      style={{
                        marginLeft: 8,
                        padding: "2px 6px",
                        backgroundColor: "#f1f5f9",
                        color: "#475569",
                        borderRadius: 3,
                        fontSize: 12,
                      }}
                    >
                      Child of {parentQuestionById[faq.parent_id] ?? `#${faq.parent_id}`}
                    </span>
                  )}
                  {!faq.is_active && (
                    <span
                      style={{
                        marginLeft: 8,
                        padding: "2px 6px",
                        backgroundColor: "#999",
                        color: "white",
                        borderRadius: 3,
                        fontSize: 12,
                      }}
                    >
                      Inactive
                    </span>
                  )}
                </div>
                <p style={{ margin: "4px 0 8px", color: "#666" }}>
                  A: {faq.answer}
                </p>
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => handleDeleteFAQ(faq.id)}
                    style={{
                      padding: "6px 12px",
                      backgroundColor: "#f44336",
                      color: "white",
                      border: "none",
                      borderRadius: 4,
                      cursor: "pointer",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

