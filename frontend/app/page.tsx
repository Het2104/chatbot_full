"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createChatbot, getChatbots, deleteChatbot } from "../services/api";
import { Plus, MessageSquare, Trash2, ArrowRight, Bot, Sparkles, LayoutDashboard } from 'lucide-react';

type Chatbot = {
  id: string | number;
  name?: string;
  description?: string;
};

export default function Home() {
  const router = useRouter();
  const [chatbots, setChatbots] = useState<Chatbot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const loadChatbots = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await getChatbots()) as Chatbot[];
      setChatbots(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chatbots");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChatbots();
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Name is required");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await createChatbot({ name: name.trim(), description: description.trim() });
      setName("");
      setDescription("");
      setShowCreateForm(false);
      await loadChatbots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chatbot");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (chatbotId: string | number, chatbotName: string) => {
    if (!confirm(`Are you sure you want to delete "${chatbotName}"? This will delete all workflows and nodes associated with this chatbot.`)) {
      return;
    }

    setError(null);
    try {
      await deleteChatbot(chatbotId);
      await loadChatbots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete chatbot");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-8 md:py-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-xs font-semibold mb-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <Sparkles size={14} />
            <span>AI Agent Management</span>
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight text-slate-900 mb-4 max-w-4xl mx-auto leading-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 via-primary-800 to-slate-900 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-100">
            Supercharge your workflows with <span className="text-primary-600">Intelligent Agents</span>
          </h1>
          <p className="text-base md:text-lg text-slate-500 max-w-2xl mx-auto mb-6 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-200">
            Create, manage, and deploy powerful AI chatbots to automate support, sales, and internal processes.
          </p>

          {!showCreateForm && (
            <button
              onClick={() => setShowCreateForm(true)}
              className="group bg-slate-900 text-white px-6 py-3 rounded-full font-bold text-base shadow-xl shadow-slate-200 hover:bg-primary-600 hover:scale-105 transition-all duration-300 animate-in fade-in slide-in-from-bottom-4 duration-1000 delay-300 flex items-center gap-2 mx-auto"
            >
              <Plus size={18} className="group-hover:rotate-90 transition-transform duration-300" />
              Create New Agent
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Create Form Modal/Card */}
        {showCreateForm && (
          <div className="max-w-xl mx-auto mb-10 animate-in fade-in zoom-in-95 duration-300">
            <div className="bg-white rounded-3xl p-6 shadow-2xl shadow-primary-900/10 border border-slate-100 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-400 via-primary-600 to-primary-400"></div>
              <div className="text-center mb-6">
                <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center mx-auto mb-3 text-primary-600">
                  <Bot size={24} />
                </div>
                <h2 className="text-xl font-bold text-slate-800">Configure Your New Agent</h2>
                <p className="text-sm text-slate-500">Give your agent an identity to get started.</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Agent Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-100 focus:border-primary-500 focus:outline-none transition-all placeholder:text-slate-400 font-medium text-sm"
                    placeholder="e.g. Support Wizard"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">Description <span className="text-slate-400 font-normal">(Optional)</span></label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-100 focus:border-primary-500 focus:outline-none transition-all placeholder:text-slate-400 text-sm"
                    placeholder="What will this agent do?"
                  />
                </div>

                {error && (
                  <div className="p-3 bg-red-50 text-red-600 rounded-xl text-xs font-medium flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-red-500 rounded-full"></div>
                    {error}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="flex-1 py-3 rounded-xl font-bold text-slate-600 hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 bg-black text-white py-3 rounded-xl font-bold hover:bg-slate-800 transition-all shadow-lg shadow-slate-200 disabled:opacity-70 disabled:shadow-none text-sm"
                  >
                    {submitting ? "Creating..." : "Launch Agent"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Chatbots Grid */}
        <div className="space-y-6">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <LayoutDashboard className="text-slate-400" size={24} />
              Your Agents
            </h3>
            {chatbots.length > 0 && !showCreateForm && (
              <span className="text-sm font-medium text-slate-500 bg-white px-3 py-1 rounded-full border border-slate-100 shadow-sm">{chatbots.length} Active</span>
            )}
          </div>

          {loading ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-64 bg-white rounded-3xl shadow-sm border border-slate-100 animate-pulse"></div>
              ))}
            </div>
          ) : chatbots.length === 0 ? (
            <div className="text-center py-24 bg-white rounded-3xl border-2 border-dashed border-slate-200">
              <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6 text-slate-300">
                <Bot size={40} />
              </div>
              <h3 className="text-xl font-bold text-slate-700 mb-2">No agents yet</h3>
              <p className="text-slate-400 max-w-md mx-auto mb-8">Get started by creating your first AI agent to handle tasks and conversations.</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="bg-primary-50 text-primary-700 px-6 py-3 rounded-full font-bold hover:bg-primary-100 transition-all"
              >
                Create Your First Agent
              </button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {chatbots.map((chatbot) => (
                <div
                  key={chatbot.id}
                  className="bg-white rounded-3xl p-6 shadow-sm hover:shadow-xl hover:shadow-slate-200/50 border border-slate-100 hover:border-slate-200 transition-all duration-300 group flex flex-col h-full relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-slate-200 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>

                  <div className="flex justify-between items-start mb-6">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 flex items-center justify-center text-slate-600 shadow-sm group-hover:scale-110 transition-transform duration-300 relative">
                      <Bot size={28} />
                      <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 border-2 border-white rounded-full"></div>
                    </div>
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(chatbot.id, chatbot.name || "Untitled");
                        }}
                        className="w-8 h-8 flex items-center justify-center rounded-full text-slate-300 hover:bg-red-50 hover:text-red-500 transition-all"
                        title="Delete Agent"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>

                  <div className="mb-8 flex-1">
                    <h3 className="text-xl font-bold text-slate-800 mb-2 group-hover:text-primary-700 transition-colors line-clamp-1">{chatbot.name || "Untitled Agent"}</h3>
                    <p className="text-slate-500 text-sm leading-relaxed line-clamp-2">{chatbot.description || "No description provided."}</p>
                  </div>

                  <div className="flex gap-3 mt-auto">
                    <button
                      onClick={() => router.push(`/dashboard/${chatbot.id}`)}
                      className="flex-1 bg-slate-900 text-white py-3 rounded-xl font-bold text-sm hover:bg-primary-600 transition-all shadow-lg shadow-slate-200 hover:shadow-primary-200 flex items-center justify-center gap-2 group/btn"
                    >
                      Open Dashboard
                      <ArrowRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
