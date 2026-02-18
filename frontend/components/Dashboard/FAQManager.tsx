"use client";

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit2, ChevronDown, ChevronRight, HelpCircle } from 'lucide-react';
import { getFAQs, createFAQ, deleteFAQ, updateFAQ } from '../../services/api';

interface FAQManagerProps {
    chatbotId: string;
}

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

export default function FAQManager({ chatbotId }: FAQManagerProps) {
    const [faqs, setFAQs] = useState<FAQ[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showForm, setShowForm] = useState(false);

    // Form State
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [parentId, setParentId] = useState<string>("");
    const [submitting, setSubmitting] = useState(false);

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
        if (chatbotId) {
            loadFAQs();
        }
    }, [chatbotId]);

    const handleCreateFAQ = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || !answer.trim()) return;

        setSubmitting(true);
        try {
            await createFAQ(chatbotId, {
                question,
                answer,
                parent_id: parentId ? Number(parentId) : null,
                is_active: true
            });
            setQuestion("");
            setAnswer("");
            setParentId("");
            setShowForm(false);
            await loadFAQs();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create FAQ");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteFAQ = async (id: number) => {
        if (!confirm("Are you sure?")) return;
        try {
            await deleteFAQ(id);
            await loadFAQs();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete FAQ");
        }
    };

    const parentFAQs = faqs.filter(f => f.parent_id === null);
    const getChildren = (id: number) => faqs.filter(f => f.parent_id === id);

    return (
        <section className="h-full w-full p-8 overflow-y-auto bg-slate-50/50">
            <div className="max-w-4xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-800 tracking-tight">FAQ Management</h2>
                        <p className="text-slate-500 mt-1">Manage the questions your bot can answer automatically.</p>
                    </div>
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="bg-black text-white px-5 py-2.5 rounded-xl text-sm font-medium shadow-lg shadow-slate-200 flex items-center gap-2 hover:bg-slate-800 hover:scale-105 transition-all active:scale-95"
                    >
                        {showForm ? <Trash2 size={16} /> : <Plus size={16} />}
                        {showForm ? 'Cancel' : 'Add Question'}
                    </button>
                </div>

                {error && <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 shadow-sm border border-red-100 flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    {error}
                </div>}

                {showForm && (
                    <div className="bg-white p-8 rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 mb-8 animate-in fade-in zoom-in-95 duration-200">
                        <h3 className="font-bold text-lg mb-6 text-slate-800 border-b border-slate-50 pb-4">Create New Question</h3>
                        <form onSubmit={handleCreateFAQ} className="space-y-5">
                            <div className="grid grid-cols-2 gap-6">
                                <div className="col-span-2">
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Question</label>
                                    <input
                                        type="text"
                                        value={question}
                                        onChange={(e) => setQuestion(e.target.value)}
                                        className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-100 focus:border-primary-500 focus:outline-none transition-all placeholder:text-slate-300"
                                        placeholder="e.g. What are your opening hours?"
                                        required
                                    />
                                </div>
                                <div className="col-span-2">
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Answer</label>
                                    <textarea
                                        value={answer}
                                        onChange={(e) => setAnswer(e.target.value)}
                                        className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-100 focus:border-primary-500 focus:outline-none transition-all placeholder:text-slate-300 min-h-[100px]"
                                        rows={3}
                                        placeholder="e.g. We are open Mon-Fri from 9am to 6pm..."
                                        required
                                    />
                                </div>
                                <div className="col-span-2 sm:col-span-1">
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Parent Topic (Optional)</label>
                                    <select
                                        value={parentId}
                                        onChange={(e) => setParentId(e.target.value)}
                                        className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-100 focus:border-primary-500 focus:outline-none transition-all bg-white"
                                    >
                                        <option value="">None (Top Level)</option>
                                        {parentFAQs.map(faq => (
                                            <option key={faq.id} value={faq.id}>{faq.question}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex justify-end pt-4">
                                <button
                                    type="submit"
                                    disabled={submitting}
                                    className="bg-black text-white px-8 py-3 rounded-xl font-bold hover:bg-slate-800 transition-all hover:shadow-lg disabled:opacity-50 disabled:shadow-none"
                                >
                                    {submitting ? "Saving..." : "Save Question"}
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                <div className="space-y-4">
                    {loading && (
                        <div className="space-y-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="h-32 bg-white rounded-2xl shadow-sm border border-slate-100 animate-pulse"></div>
                            ))}
                        </div>
                    )}

                    {!loading && faqs.length === 0 && (
                        <div className="text-center py-16 bg-white rounded-3xl border border-dashed border-slate-200 shadow-sm">
                            <div className="w-16 h-16 bg-primary-50 rounded-full flex items-center justify-center mx-auto mb-4 text-primary-400">
                                <HelpCircle size={32} className="opacity-50" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-700">No FAQs yet</h3>
                            <p className="text-slate-400">Create your first question to help your users.</p>
                        </div>
                    )}

                    {parentFAQs.map(faq => (
                        <div key={faq.id} className="group">
                            <div className="bg-white rounded-2xl shadow-sm hover:shadow-md border border-slate-200 p-6 transition-all duration-300 relative overflow-hidden">
                                <div className="absolute top-0 left-0 w-1 h-full bg-primary-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                <div className="flex justify-between items-start gap-4">
                                    <div className="flex-1">
                                        <h3 className="font-bold text-slate-800 text-lg mb-2">{faq.question}</h3>
                                        <p className="text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100 text-sm">{faq.answer}</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleDeleteFAQ(faq.id)}
                                            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100"
                                            title="Delete FAQ"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Children */}
                            {getChildren(faq.id).some(c => c) && (
                                <div className="ml-8 mt-3 pl-6 border-l-2 border-slate-100 space-y-3">
                                    {getChildren(faq.id).map(child => (
                                        <div key={child.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 relative group/child hover:border-primary-200 transition-colors">
                                            <div className="flex justify-between items-start gap-4">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="text-[10px] font-bold uppercase tracking-wider bg-primary-50 text-primary-600 px-2.5 py-1 rounded-md">Follow-up</span>
                                                        <h4 className="font-semibold text-slate-800 text-sm">{child.question}</h4>
                                                    </div>
                                                    <p className="text-slate-600 text-sm pl-1">{child.answer}</p>
                                                </div>
                                                <button
                                                    onClick={() => handleDeleteFAQ(child.id)}
                                                    className="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover/child:opacity-100"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
