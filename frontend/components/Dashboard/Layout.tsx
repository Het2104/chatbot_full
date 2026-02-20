"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from './Sidebar';
import ChatInterface from './ChatInterface';
import Workflows from './Workflows';
import FAQManager from './FAQManager';
import KnowledgeBase from './KnowledgeBase';
import { getChatbots } from '../../services/api';
import { useAuth } from '@/contexts/AuthContext';
import { NavBar } from '@/components/NavBar';

type ViewType = 'chat' | 'workflows' | 'faq' | 'knowledge';

interface DashboardLayoutProps {
    chatbotId: string;
}

export default function DashboardLayout({ chatbotId }: DashboardLayoutProps) {
    const router = useRouter();
    const { isAuthenticated, loading: authLoading } = useAuth();
    const [currentView, setCurrentView] = useState<ViewType>('chat');
    const [chatbotName, setChatbotName] = useState("");

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, authLoading, router]);

    useEffect(() => {
        if (isAuthenticated) {
            getChatbots().then((bots: any) => {
                if (Array.isArray(bots)) {
                    const bot = bots.find((b: any) => String(b.id) === String(chatbotId));
                    if (bot) setChatbotName(bot.name);
                }
            }).catch(err => console.error("Failed to load bot name", err));
        }
    }, [chatbotId, isAuthenticated]);

    // Show loading while checking authentication
    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-lg">Loading...</div>
            </div>
        );
    }

    // Don't render if not authenticated (will redirect)
    if (!isAuthenticated) {
        return null;
    }

    const renderContent = () => {
        switch (currentView) {
            case 'chat':
                return <ChatInterface chatbotId={chatbotId} />;
            case 'workflows':
                return <Workflows chatbotId={chatbotId} />;
            case 'faq':
                return <FAQManager chatbotId={chatbotId} />;
            case 'knowledge':
                return <KnowledgeBase />;
            default:
                return <ChatInterface chatbotId={chatbotId} />;
        }
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <NavBar />
            <div className="bg-slate-50 text-slate-800 font-sans h-[calc(100vh-64px)] flex overflow-hidden">
                <Sidebar
                    currentView={currentView}
                    onViewChange={(view) => setCurrentView(view as ViewType)}
                    chatbotName={chatbotName || `Chatbot #${chatbotId}`}
                />

                <main className="flex-1 h-full overflow-hidden relative bg-slate-50">
                    {renderContent()}
                </main>
            </div>
        </div>
    );
}
