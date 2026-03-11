"use client";

import React, { useEffect, useState } from 'react';
import { getChatbot, updateWidgetSettings } from '../../services/api';

const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface EmbedWidgetProps {
    chatbotId: string;
}

type ChatbotDetail = {
    id: number;
    name: string;
    embed_key: string;
    widget_color: string;
    widget_welcome_message: string;
    widget_position: string;
};

export default function EmbedWidget({ chatbotId }: EmbedWidgetProps) {
    const [chatbot, setChatbot] = useState<ChatbotDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [color, setColor] = useState('#2563EB');
    const [welcome, setWelcome] = useState('Hi! How can I help you?');
    const [position, setPosition] = useState('bottom-right');

    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        setLoading(true);
        setError(null);
        getChatbot(chatbotId)
            .then((data) => {
                const d = data as ChatbotDetail;
                setChatbot(d);
                setColor(d.widget_color);
                setWelcome(d.widget_welcome_message);
                setPosition(d.widget_position);
            })
            .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
            .finally(() => setLoading(false));
    }, [chatbotId]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        setSaved(false);
        setError(null);
        try {
            const updated = (await updateWidgetSettings(chatbotId, {
                widget_color: color,
                widget_welcome_message: welcome,
                widget_position: position,
            })) as ChatbotDetail;
            setChatbot(updated);
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save');
        } finally {
            setSaving(false);
        }
    };

    const embedCode = chatbot?.embed_key
        ? `<script src="${BASE_API_URL}/widget/${chatbot.embed_key}.js"></script>`
        : '';

    const handleCopy = () => {
        if (!embedCode) return;
        navigator.clipboard.writeText(embedCode);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full text-slate-400">
                Loading widget settings…
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full text-red-500">
                {error}
            </div>
        );
    }

    return (
        <div className="h-full overflow-y-auto bg-slate-50 p-6 font-sans">
            <div className="max-w-2xl mx-auto space-y-6">

                {/* Header */}
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">Embed Widget</h2>
                    <p className="text-slate-500 mt-1 text-sm">
                        Add a floating chat bubble to any website with one line of code.
                    </p>
                </div>

                {/* Settings Form */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                    <h3 className="font-semibold text-slate-700 mb-4">Appearance</h3>
                    <form onSubmit={handleSave} className="space-y-5">

                        {/* Color */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-2">
                                Bubble Color
                            </label>
                            <div className="flex items-center gap-3">
                                <input
                                    type="color"
                                    value={color}
                                    onChange={(e) => setColor(e.target.value)}
                                    className="w-12 h-10 rounded-lg border border-slate-200 cursor-pointer p-0.5"
                                />
                                <input
                                    type="text"
                                    value={color}
                                    onChange={(e) => setColor(e.target.value)}
                                    className="w-32 px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-300"
                                />
                                {/* Live preview bubble */}
                                <div
                                    className="w-10 h-10 rounded-full flex items-center justify-center text-white text-lg shadow-md flex-shrink-0"
                                    style={{ backgroundColor: color }}
                                >
                                    💬
                                </div>
                            </div>
                        </div>

                        {/* Welcome message */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-2">
                                Welcome Message
                            </label>
                            <input
                                type="text"
                                value={welcome}
                                onChange={(e) => setWelcome(e.target.value)}
                                placeholder="Hi! How can I help you?"
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-300"
                            />
                        </div>

                        {/* Position */}
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-2">
                                Position
                            </label>
                            <div className="flex gap-4">
                                {(['bottom-right', 'bottom-left'] as const).map((pos) => (
                                    <label
                                        key={pos}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg border cursor-pointer text-sm font-medium transition-all ${position === pos
                                            ? 'border-primary-400 bg-primary-50 text-primary-700'
                                            : 'border-slate-200 text-slate-500 hover:border-slate-300'
                                            }`}
                                    >
                                        <input
                                            type="radio"
                                            name="position"
                                            value={pos}
                                            checked={position === pos}
                                            onChange={() => setPosition(pos)}
                                            className="sr-only"
                                        />
                                        {pos === 'bottom-right' ? '↘ Bottom Right' : '↙ Bottom Left'}
                                    </label>
                                ))}
                            </div>
                        </div>

                        {/* Save button */}
                        <div className="flex items-center gap-3 pt-1">
                            <button
                                type="submit"
                                disabled={saving}
                                className="px-5 py-2 bg-slate-900 text-white font-semibold rounded-xl text-sm hover:bg-black transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                                {saving ? 'Saving…' : 'Save Settings'}
                            </button>
                            {saved && (
                                <span className="text-green-600 font-medium text-sm">✓ Saved!</span>
                            )}
                        </div>
                    </form>
                </div>

                {/* Embed Code */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                    <h3 className="font-semibold text-slate-700 mb-1">Embed Code</h3>
                    <p className="text-slate-500 text-sm mb-4">
                        Paste this inside the <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">&lt;body&gt;</code> of any website to show the floating chat bubble.
                    </p>
                    <div className="relative">
                        <pre className="bg-slate-900 text-emerald-300 rounded-xl px-4 py-3.5 text-xs overflow-x-auto select-all leading-relaxed">
                            {embedCode}
                        </pre>
                        <button
                            onClick={handleCopy}
                            className={`absolute top-2 right-2 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${copied
                                ? 'bg-green-500 text-white'
                                : 'bg-slate-700 text-slate-200 hover:bg-slate-600'
                                }`}
                        >
                            {copied ? '✓ Copied!' : 'Copy'}
                        </button>
                    </div>
                </div>

                {/* Live Preview */}
                {chatbot?.embed_key && (
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                        <h3 className="font-semibold text-slate-700 mb-1">Live Preview</h3>
                        <p className="text-slate-500 text-sm mb-4">
                            This is what visitors will see when they open the chat bubble.
                        </p>
                        <iframe
                            key={`${chatbot.embed_key}-${color}-${welcome}`}
                            src={`/embed/${chatbot.embed_key}`}
                            className="w-full rounded-xl border border-slate-200 shadow-inner"
                            style={{ height: 460 }}
                            title="Widget Preview"
                        />
                    </div>
                )}

            </div>
        </div>
    );
}
