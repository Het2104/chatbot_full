"use client";

import React from 'react';
import { MessageSquare, Network, HelpCircle, Book, LogOut, User } from 'lucide-react';

interface SidebarProps {
    currentView: string;
    onViewChange: (view: string) => void;
    chatbotName?: string;
}

export default function Sidebar({ currentView, onViewChange, chatbotName = "AI Chatbot" }: SidebarProps) {
    const navItems = [
        { id: 'chat', label: 'Chat Interface', icon: <MessageSquare size={20} /> },
        { id: 'workflows', label: 'Workflows', icon: <Network size={20} /> },
        { id: 'faq', label: 'FAQ Manager', icon: <HelpCircle size={20} /> },
        { id: 'knowledge', label: 'Knowledge Base', icon: <Book size={20} /> },
    ];

    return (
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col flex-none z-50 h-full font-sans shadow-sm">
            {/* Logo Area */}
            <div className="p-6">
                <div className="flex items-center gap-3 text-slate-800">
                    <div className="w-9 h-9 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center text-white shadow-md shadow-primary-200">
                        <BotIcon />
                    </div>
                    <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700">AI Chatbot</span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 py-3 space-y-1.5 overflow-y-auto">
                {navItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => onViewChange(item.id)}
                        className={`w-full flex items-center gap-3.5 px-4 py-3.5 text-sm font-medium rounded-xl transition-all duration-200 group ${currentView === item.id
                            ? 'bg-primary-50 text-primary-700 shadow-sm ring-1 ring-primary-100 translate-x-1'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900 hover:translate-x-1'
                            }`}
                    >
                        <span className={`transition-colors ${currentView === item.id ? 'text-primary-600' : 'text-slate-400 group-hover:text-slate-600'}`}>
                            {item.icon}
                        </span>
                        {item.label}
                    </button>
                ))}
            </nav>

            {/* User Profile */}
            <div className="p-4 border-t border-slate-100">
                <div className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50 transition-colors cursor-pointer group border border-transparent hover:border-slate-100">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-100 to-primary-50 flex items-center justify-center text-primary-600 font-bold text-sm relative shadow-inner">
                        {chatbotName.slice(0, 2).toUpperCase()}
                        <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full shadow-sm"></span>
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                        <p className="text-sm font-bold text-slate-700 truncate group-hover:text-primary-700 transition-colors">{chatbotName}</p>
                        <p className="text-xs text-slate-500 truncate">Online</p>
                    </div>
                    <a href="/" className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all" title="Exit to Home">
                        <LogOut size={18} />
                    </a>
                </div>
            </div>
        </aside>
    );
}

function BotIcon() {
    return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 8V4H8" />
            <rect width="16" height="12" x="4" y="8" rx="2" />
            <path d="M2 14h2" />
            <path d="M20 14h2" />
            <path d="M15 13v2" />
            <path d="M9 13v2" />
        </svg>
    );
}
