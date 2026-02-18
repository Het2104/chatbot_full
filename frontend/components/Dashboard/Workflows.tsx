"use client";

import React, { useState, useEffect } from 'react';
import { Plus, Pointer, GripHorizontal, ArrowRight } from 'lucide-react';
import { getWorkflows, createWorkflow } from '../../services/api';
import { useRouter } from 'next/navigation';

interface WorkflowsProps {
    chatbotId: string;
}

type Workflow = {
    id: string | number;
    name?: string;
    is_active?: boolean;
};

export default function Workflows({ chatbotId }: WorkflowsProps) {
    const router = useRouter();
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [loading, setLoading] = useState(true);
    const [newWorkflowName, setNewWorkflowName] = useState("");
    const [creating, setCreating] = useState(false);

    const loadWorkflows = async () => {
        setLoading(true);
        try {
            const data = (await getWorkflows(chatbotId)) as Workflow[];
            setWorkflows(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (chatbotId) loadWorkflows();
    }, [chatbotId]);

    const handleCreate = async () => {
        if (!newWorkflowName.trim()) return;
        setCreating(true);
        try {
            await createWorkflow(chatbotId, { name: newWorkflowName });
            setNewWorkflowName("");
            await loadWorkflows();
        } catch (err) {
            alert("Failed to create workflow");
        } finally {
            setCreating(false);
        }
    };

    return (
        <section className="h-full w-full bg-slate-50/50">
            <div className="grid grid-cols-12 h-full">
                {/* Sidebar List */}
                <div className="col-span-3 bg-white border-r border-slate-200 flex flex-col h-full shadow-sm">
                    <div className="p-5 border-b border-slate-100 bg-white/80 backdrop-blur-sm z-10 sticky top-0">
                        <h3 className="font-bold text-slate-800 text-lg mb-4 flex items-center gap-2">
                            Workflows <span className="text-xs font-normal text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{workflows.length}</span>
                        </h3>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={newWorkflowName}
                                onChange={(e) => setNewWorkflowName(e.target.value)}
                                placeholder="New workflow name..."
                                className="flex-1 px-3.5 py-2 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all bg-slate-50 focus:bg-white"
                            />
                            <button
                                onClick={handleCreate}
                                disabled={creating || !newWorkflowName.trim()}
                                className="bg-black hover:bg-slate-800 text-white px-3.5 py-2 rounded-xl shadow-lg shadow-slate-200 flex items-center justify-center disabled:opacity-50 disabled:shadow-none transition-all duration-200 transform active:scale-95"
                            >
                                <Plus size={18} />
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-3 space-y-2">
                        {loading && (
                            <div className="space-y-3 p-2">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse"></div>
                                ))}
                            </div>
                        )}

                        {!loading && workflows.length === 0 && (
                            <div className="text-center p-8 text-slate-400">
                                <p className="text-sm">No workflows yet.</p>
                            </div>
                        )}

                        {workflows.map(workflow => (
                            <div
                                key={workflow.id}
                                className="p-4 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-200 transition-all group relative bg-white shadow-sm hover:shadow-md cursor-default"
                            >
                                <div className="flex justify-between items-center">
                                    <span
                                        onClick={() => router.push(`/workflows/${workflow.id}`)}
                                        className="font-semibold text-slate-700 group-hover:text-primary-700 transition-colors cursor-pointer"
                                    >
                                        {workflow.name || "Untitled Workflow"}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Placeholder Canvas Area */}
                <div className="col-span-9 relative bg-slate-50 overflow-hidden flex flex-col items-center justify-center text-slate-400">
                    <div className="absolute inset-0" style={{
                        backgroundColor: '#f8fafc',
                        backgroundImage: 'radial-gradient(#e2e8f0 1.5px, transparent 1.5px)',
                        backgroundSize: '24px 24px'
                    }}></div>

                    <div className="z-10 bg-white/80 backdrop-blur-xl p-10 rounded-3xl shadow-xl shadow-slate-200/50 border border-white text-center max-w-md transform transition-all hover:scale-[1.02] duration-500">
                        <div className="w-20 h-20 bg-gradient-to-br from-primary-100 to-primary-50 rounded-2xl flex items-center justify-center mx-auto mb-6 text-primary-600 shadow-inner">
                            <Pointer size={40} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-800 mb-3">Select a Workflow</h3>
                        <p className="text-slate-500 leading-relaxed">
                            Design conversational flows visually. Select a workflow from the sidebar to open the editor canvas.
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
}
