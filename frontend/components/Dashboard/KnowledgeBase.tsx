"use client";

import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, FileText, Trash2, CheckCircle, AlertCircle, Link, Globe, Lock } from 'lucide-react';
import { getIndexedPdfs, uploadPdf, deletePdf, ingestUrl, getIndexedUrls, deleteUrl } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

type IndexedPdf = {
    filename: string;
    size_bytes: number;
    size_mb: number;
    uploaded_at: number;
};

type IndexedUrl = {
    id: number;
    url: string;
    title: string | null;
    num_chunks: number;
    indexed_at: string;
};

export default function KnowledgeBase() {
    const { role } = useAuth();
    const isAdmin = role === 'admin';
    const [pdfs, setPdfs] = useState<IndexedPdf[]>([]);
    const [urls, setUrls] = useState<IndexedUrl[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [urlInput, setUrlInput] = useState('');
    const [ingestingUrl, setIngestingUrl] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'pdfs' | 'urls'>('pdfs');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadPdfs = async () => {
        try {
            const data = await getIndexedPdfs() as { pdfs: IndexedPdf[] };
            setPdfs(data.pdfs || []);
        } catch (err) {
            console.error(err);
        }
    };

    const loadUrls = async () => {
        try {
            const data = await getIndexedUrls() as IndexedUrl[];
            setUrls(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        const loadAll = async () => {
            setLoading(true);
            await Promise.all([loadPdfs(), loadUrls()]);
            setLoading(false);
        };
        loadAll();
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

    const handleUrlIngest = async () => {
        const url = urlInput.trim();
        if (!url) return;

        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            setError('URL must start with http:// or https://');
            return;
        }

        setIngestingUrl(true);
        setError(null);

        try {
            const result = await ingestUrl(url) as { success: boolean; message: string; error?: string };
            if (result.success) {
                setUrlInput('');
                setActiveTab('urls');
                await loadUrls();
            } else {
                setError(result.error || 'Failed to index URL');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to index URL');
        } finally {
            setIngestingUrl(false);
        }
    };

    const handleDeleteUrl = async (id: number, url: string) => {
        if (!confirm(`Remove "${url}" from the knowledge base?`)) return;
        try {
            await deleteUrl(id);
            await loadUrls();
        } catch (err) {
            alert('Failed to delete URL');
        }
    };

    return (
        <section className="h-full w-full p-8 overflow-y-auto bg-slate-50/50">
            <div className="max-w-6xl mx-auto">
                <div className="mb-10">
                    <h2 className="text-2xl font-bold text-slate-800 tracking-tight">Knowledge Base</h2>
                    <p className="text-slate-500 mt-1">
                        {isAdmin
                            ? 'Upload documents or add website URLs to train the AI on your data.'
                            : 'Browse the documents and websites the AI has been trained on.'}
                    </p>
                </div>

                {error && <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 flex items-center gap-2 border border-red-100"><AlertCircle size={18} /> {error}</div>}

                <div className={`grid grid-cols-1 ${isAdmin ? 'lg:grid-cols-12' : ''} gap-8`}>
                    {/* Left column: PDF upload + URL ingest — admin only */}
                    {isAdmin && (
                    <div className="lg:col-span-4 flex flex-col gap-6">
                        {/* PDF Upload Card */}
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`bg-gradient-to-br from-white to-slate-50 border-2 border-dashed border-primary-200 rounded-2xl p-10 flex flex-col items-center justify-center text-center h-[280px] hover:bg-primary-50/50 hover:border-primary-400 hover:scale-[1.02] transition-all cursor-pointer shadow-sm group ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
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
                            <h3 className="text-slate-800 font-bold text-lg mb-2 group-hover:text-primary-700 transition-colors">{uploading ? "Uploading..." : "Upload PDF"}</h3>
                            <p className="text-sm text-slate-500 max-w-[200px] leading-relaxed">
                                Click to select a PDF document.
                                <br /><span className="text-xs opacity-70 mt-2 block">Max 10MB per file.</span>
                            </p>
                        </div>

                        {/* URL Ingest Card */}
                        <div className="bg-gradient-to-br from-white to-slate-50 border-2 border-dashed border-blue-200 rounded-2xl p-8 flex flex-col items-center text-center shadow-sm">
                            <div className="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mb-4 shadow-inner">
                                <Globe size={32} />
                            </div>
                            <h3 className="text-slate-800 font-bold text-lg mb-1">Add Website URL</h3>
                            <p className="text-sm text-slate-500 mb-5 leading-relaxed">
                                Index any public webpage into the knowledge base.
                            </p>
                            <div className="w-full flex flex-col gap-2">
                                <input
                                    type="url"
                                    value={urlInput}
                                    onChange={(e) => setUrlInput(e.target.value)}
                                    onKeyDown={(e) => { if (e.key === 'Enter') handleUrlIngest(); }}
                                    placeholder="https://example.com/page"
                                    disabled={ingestingUrl}
                                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-300 focus:border-blue-400 disabled:opacity-50 bg-white"
                                />
                                <button
                                    onClick={handleUrlIngest}
                                    disabled={ingestingUrl || !urlInput.trim()}
                                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-600 disabled:bg-slate-200 disabled:text-slate-400 text-white text-sm font-semibold transition-colors"
                                >
                                    {ingestingUrl ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Indexing...
                                        </>
                                    ) : (
                                        <>
                                            <Link size={15} />
                                            Index URL
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                    )}

                    {/* Right column: tabbed list of PDFs and URLs */}
                    <div className={isAdmin ? 'lg:col-span-8' : 'w-full'}>
                        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden">
                            {/* Tabs */}
                            <div className="px-8 py-4 border-b border-slate-100 flex items-center gap-4">
                                <button
                                    onClick={() => setActiveTab('pdfs')}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${activeTab === 'pdfs' ? 'bg-primary-50 text-primary-700' : 'text-slate-500 hover:text-slate-700'}`}
                                >
                                    <FileText size={15} />
                                    Documents
                                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{pdfs.length}</span>
                                </button>
                                <button
                                    onClick={() => setActiveTab('urls')}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${activeTab === 'urls' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:text-slate-700'}`}
                                >
                                    <Globe size={15} />
                                    Websites
                                    <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{urls.length}</span>
                                </button>
                            </div>

                            <div className="max-h-[500px] overflow-y-auto">
                                {loading && (
                                    <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
                                        <div className="w-8 h-8 border-2 border-slate-200 border-t-primary-500 rounded-full animate-spin"></div>
                                        <span className="text-sm">Syncing...</span>
                                    </div>
                                )}

                                {/* PDFs tab */}
                                {!loading && activeTab === 'pdfs' && (
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
                                                        <p>No documents uploaded yet.</p>
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
                                                            {isAdmin && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleDelete(pdf.filename); }}
                                                                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100"
                                                                title="Delete File"
                                                            >
                                                                <Trash2 size={16} />
                                                            </button>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                )}

                                {/* URLs tab */}
                                {!loading && activeTab === 'urls' && (
                                    <table className="w-full text-left text-sm">
                                        <thead className="bg-slate-50/50 text-slate-500 text-xs uppercase tracking-wider font-semibold sticky top-0 backdrop-blur-sm z-10">
                                            <tr>
                                                <th className="px-8 py-4">Website</th>
                                                <th className="px-8 py-4 text-right">Chunks</th>
                                                <th className="px-8 py-4 w-16"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-50">
                                            {urls.length === 0 ? (
                                                <tr><td colSpan={3} className="px-8 py-16 text-center text-slate-400">
                                                    <div className="flex flex-col items-center gap-2">
                                                        <Globe size={32} className="opacity-20" />
                                                        <p>No websites indexed yet.</p>
                                                        {isAdmin
                                                            ? <p className="text-xs">Paste a URL on the left to get started.</p>
                                                            : <p className="text-xs flex items-center gap-1"><Lock size={12} /> Only admins can add content.</p>
                                                        }
                                                    </div>
                                                </td></tr>
                                            ) : (
                                                urls.map((item) => (
                                                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors group">
                                                        <td className="px-8 py-5">
                                                            <div className="flex items-center gap-4">
                                                                <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-500 flex items-center justify-center border border-blue-100 shadow-sm flex-shrink-0">
                                                                    <Globe size={20} />
                                                                </div>
                                                                <div className="min-w-0">
                                                                    <p className="font-medium text-slate-700 group-hover:text-blue-700 transition-colors truncate max-w-[320px]">
                                                                        {item.title || item.url}
                                                                    </p>
                                                                    <p className="text-xs text-slate-400 truncate max-w-[320px]">{item.url}</p>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="px-8 py-5 text-right">
                                                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-600 border border-blue-100 shadow-sm">
                                                                <CheckCircle size={10} className="stroke-[3]" /> {item.num_chunks} chunks
                                                            </span>
                                                        </td>
                                                        <td className="px-8 py-5 text-right">
                                                            {isAdmin && (
                                                            <button
                                                                onClick={() => handleDeleteUrl(item.id, item.url)}
                                                                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100"
                                                                title="Remove URL"
                                                            >
                                                                <Trash2 size={16} />
                                                            </button>
                                                            )}
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
