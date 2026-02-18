"use client";

import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, FileText, Trash2, CheckCircle, AlertCircle } from 'lucide-react';
import { getIndexedPdfs, uploadPdf, deletePdf } from '../../services/api';

type IndexedPdf = {
    filename: string;
    size_bytes: number;
    size_mb: number;
    uploaded_at: number;
};

export default function KnowledgeBase() {
    const [pdfs, setPdfs] = useState<IndexedPdf[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadPdfs = async () => {
        setLoading(true);
        try {
            const data = await getIndexedPdfs();
            setPdfs(data.pdfs || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadPdfs();
    }, []);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;

        const file = e.target.files[0];
        setUploading(true);
        setError(null);

        try {
            await uploadPdf(file);
            await loadPdfs();
            if (fileInputRef.current) fileInputRef.current.value = "";
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to upload PDF");
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (filename: string) => {
        if (!confirm(`Delete ${filename}?`)) return;
        try {
            await deletePdf(filename);
            await loadPdfs();
        } catch (err) {
            alert("Failed to delete file");
        }
    };

    return (
        <section className="h-full w-full p-8 overflow-y-auto bg-slate-50/50">
            <div className="max-w-6xl mx-auto">
                <div className="mb-10">
                    <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Knowledge Base</h2>
                    <p className="text-slate-500 mt-1">Upload documents to train my AI on your specific data.</p>
                </div>

                {error && <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 flex items-center gap-2 border border-red-100"><AlertCircle size={18} /> {error}</div>}

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Upload Card */}
                    <div className="lg:col-span-4">
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`bg-gradient-to-br from-white to-slate-50 border-2 border-dashed border-primary-200 rounded-2xl p-10 flex flex-col items-center justify-center text-center h-[340px] hover:bg-primary-50/50 hover:border-primary-400 hover:scale-[1.02] transition-all cursor-pointer shadow-sm group ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
                        >
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileSelect}
                                accept=".pdf"
                                className="hidden"
                            />
                            <div className="w-20 h-20 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform duration-300">
                                <UploadCloud size={40} className="drop-shadow-sm" />
                            </div>
                            <h3 className="text-slate-800 font-bold text-lg mb-2 group-hover:text-primary-700 transition-colors">{uploading ? "Uploading..." : "Click to Upload"}</h3>
                            <p className="text-sm text-slate-500 max-w-[200px] leading-relaxed">
                                Drag and drop or click to select PDF documents.
                                <br /><span className="text-xs opacity-70 mt-2 block">Max 10MB per file.</span>
                            </p>
                        </div>
                    </div>

                    {/* File List */}
                    <div className="lg:col-span-8">
                        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
                            <div className="px-8 py-6 border-b border-slate-50 bg-white flex justify-between items-center">
                                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-primary-500"></div>
                                    Uploaded Documents
                                </h3>
                                <span className="text-xs font-semibold bg-slate-100 text-slate-500 px-2.5 py-1 rounded-full">{pdfs.length} files</span>
                            </div>

                            <div className="max-h-[500px] overflow-y-auto">
                                {loading && (
                                    <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
                                        <div className="w-8 h-8 border-2 border-slate-200 border-t-primary-500 rounded-full animate-spin"></div>
                                        <span className="text-sm">Syncing files...</span>
                                    </div>
                                )}

                                {!loading && (
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-slate-50/50 text-slate-500 text-xs uppercase tracking-wider font-semibold sticky top-0 backdrop-blur-sm z-10">
                                            <tr>
                                                <th className="px-8 py-4">Filename</th>
                                                <th className="px-8 py-4 text-right">Status</th>
                                                <th className="px-8 py-4 w-16"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-50">
                                            {pdfs.length === 0 ? (
                                                <tr><td colSpan={3} className="px-8 py-16 text-center text-slate-400">
                                                    <div className="flex flex-col items-center gap-2">
                                                        <FileText size={32} className="opacity-20" />
                                                        <p>No documents found.</p>
                                                    </div>
                                                </td></tr>
                                            ) : (
                                                pdfs.map((pdf, idx) => (
                                                    <tr key={idx} className="hover:bg-slate-50/80 transition-colors group">
                                                        <td className="px-8 py-5">
                                                            <div className="flex items-center gap-4">
                                                                <div className="w-10 h-10 rounded-lg bg-red-50 text-red-500 flex items-center justify-center border border-red-100 shadow-sm">
                                                                    <FileText size={20} />
                                                                </div>
                                                                <div>
                                                                    <p className="font-medium text-slate-700 group-hover:text-primary-700 transition-colors">{pdf.filename}</p>
                                                                    <p className="text-xs text-slate-400">PDF • {(pdf.size_mb || 0).toFixed(2)} MB</p>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-5 text-right">
                                                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-green-50 text-green-600 border border-green-100 shadow-sm">
                                                                <CheckCircle size={10} className="stroke-[3]" /> Processed
                                                            </span>
                                                        </td>
                                                        <td className="px-8 py-5 text-right">
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleDelete(pdf.filename); }}
                                                                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100"
                                                                title="Delete File"
                                                            >
                                                                <Trash2 size={16} />
                                                            </button>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
