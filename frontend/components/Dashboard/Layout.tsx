"use client";

import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatInterface from './ChatInterface';
import Workflows from './Workflows';
import FAQManager from './FAQManager';
import KnowledgeBase from './KnowledgeBase';
import { getChatbots } from '../../services/api';

type ViewType = 'chat' | 'workflows' | 'faq' | 'knowledge';

interface DashboardLayoutProps {
    chatbotId: string;
}

export default function DashboardLayout({ chatbotId }: DashboardLayoutProps) {
    const [currentView, setCurrentView] = useState<ViewType>('chat');
    const [chatbotName, setChatbotName] = useState("");

    useEffect(() => {
        getChatbots().then((bots: any) => {
            if (Array.isArray(bots)) {
                const bot = bots.find((b: any) => String(b.id) === String(chatbotId));
                if (bot) setChatbotName(bot.name);
            }
        }).catch(err => console.error("Failed to load bot name", err));
    }, [chatbotId]);

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
        <div className="bg-slate-50 text-slate-800 font-sans h-screen flex overflow-hidden">
            <Sidebar
                currentView={currentView}
                onViewChange={(view) => setCurrentView(view as ViewType)}
                chatbotName={chatbotName || `Chatbot #${chatbotId}`}
            />

            <main className="flex-1 h-full overflow-hidden relative bg-slate-50">
                {renderContent()}
            </main>
        </div>
    );
}
