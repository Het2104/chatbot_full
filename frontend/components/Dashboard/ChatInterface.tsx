/**
 * ChatInterface Component
 * 
 * Main chat UI component for interacting with a chatbot.
 * 
 * Features:
 * - Real-time message exchange with bot
 * - Trigger nodes displayed as initial conversation starters
 * - FAQ suggestions at bottom for quick access
 * - Clickable option buttons for workflow navigation
 * - Auto-scroll to latest messages
 * - Loading and sending states
 * 
 * Message Flow:
 * 1. User types message or clicks option button
 * 2. Message sent to backend via sendMessage API
 * 3. Bot processes through: Workflow nodes → FAQs → RAG → Default
 * 4. Bot response displayed with optional next conversation options
 */

"use client";

import React, { useState, useEffect, useRef } from 'react';
import {
    Send,
    MoreHorizontal,
    Bot,
    User
} from 'lucide-react';
import { startChat, sendMessage, getParentFAQs, getChatbots } from '../../services/api';

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Message object displayed in chat
 */
type Message = {
    id: number;              // Unique identifier (using timestamp)
    sender: "user" | "bot";  // Who sent the message
    text: string;            // Message content
    options?: { text: string }[];  // Optional next conversation steps
    timestamp?: string;      // Display timestamp
};

/**
 * Component props
 */
interface ChatInterfaceProps {
    chatbotId: string;  // ID of the chatbot to chat with
}

export default function ChatInterface({ chatbotId }: ChatInterfaceProps) {
    // ========================================================================
    // State Management
    // ========================================================================
    
    // Chat session state
    const [sessionId, setSessionId] = useState<string | number | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    
    // UI state
    const [loading, setLoading] = useState(true);      // Initial loading
    const [sending, setSending] = useState(false);      // Sending message
    
    // Conversation options
    const [triggerNodes, setTriggerNodes] = useState<{ id: number, text: string }[]>([]);
    const [faqs, setFaqs] = useState<{ id: number, question: string }[]>([]);
    
    // Chatbot metadata
    const [botName, setBotName] = useState<string>("");
    
    // Reference for auto-scrolling to bottom
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // ========================================================================
    // Auto-scroll to bottom when messages change
    // ========================================================================
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // ========================================================================
    // Initialize chat session on component mount
    // ========================================================================
    useEffect(() => {
        /**
         * Initialize the chat interface:
         * 1. Fetch chatbot details (name)
         * 2. Start a new chat session (creates server-side session)
         * 3. Get trigger nodes (workflow starters)
         * 4. Get parent FAQs (quick-access questions)
         * 5. Display initial greeting message
         */
        const initChat = async () => {
            setLoading(true);
            try {
                // Fetch chatbot name for display in header
                getChatbots().then((bots: any) => {
                    if (Array.isArray(bots)) {
                        const bot = bots.find((b: any) => String(b.id) === String(chatbotId));
                        if (bot) setBotName(bot.name);
                    }
                }).catch(console.error);

                // Start chat session and fetch FAQs in parallel
                const [chatResult, faqResult] = await Promise.all([
                    startChat(chatbotId),
                    getParentFAQs(chatbotId).catch(() => [])
                ]);

                // Extract session data
                const result = chatResult as {
                    session_id: string | number;
                    trigger_nodes: { id: number, text: string }[];
                };
                
                setSessionId(result.session_id);
                setTriggerNodes(result.trigger_nodes || []);
                setFaqs(Array.isArray(faqResult) ? faqResult : []);

                // Display initial bot greeting
                setMessages([{
                    id: 0,
                    sender: 'bot',
                    text: "Hello! I'm your AI assistant. How can I help you optimize your workflow today?",
                    timestamp: "Today, 10:23 AM"
                }]);

            } catch (err) {
                console.error("Failed to start chat", err);
            } finally {
                setLoading(false);
            }
        };

        if (chatbotId) {
            initChat();
        }
    }, [chatbotId]);

    // ========================================================================
    // Message Handling
    // ========================================================================
    
    /**
     * Send a message to the chatbot
     * 
     * Can be triggered by:
     * - User typing and pressing Enter
     * - Clicking send button
     * - Clicking an option button (trigger, FAQ, or child node)
     * 
     * @param text - Message text (defaults to input value)
     */
    const handleSendMessage = async (text: string = inputValue) => {
        // Validation: require text and active session
        if (!text.trim() || !sessionId) return;

        // Create user message object
        const newUserMessage: Message = {
            id: Date.now(),
            sender: 'user',
            text: text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        // Immediately show user message (optimistic UI update)
        setMessages(prev => [...prev, newUserMessage]);
        setInputValue("");  // Clear input field
        setSending(true);    // Show sending state

        try {
            // Send message to backend and get bot response
            const response = await sendMessage(sessionId, text);
            
            // 🔧 FIX: Log response for debugging
            console.log('API Response:', response);
            
            // 🔧 FIX: Extract bot_response - handle both direct response and nested .data structure
            const botReply = (response as any)?.bot_response || (response as any)?.data?.bot_response || '';
            const options = (response as any)?.options || (response as any)?.data?.options || [];
            
            console.log('Bot Reply:', botReply);
            console.log('Options:', options);
            
            // 🔧 FIX: Validate response
            if (!botReply && botReply !== '') {
                console.error('No bot_response found in response:', response);
                throw new Error('Invalid response structure - missing bot_response field');
            }

            // Create bot message object
            const newBotMessage: Message = {
                id: Date.now() + 1,
                sender: 'bot',
                text: botReply,
                options: options.length > 0 ? options : undefined,  // Next conversation options (if any)
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            
            // Add bot response to chat
            setMessages(prev => [...prev, newBotMessage]);
            
            console.log('Messages updated successfully');
            
        } catch (err) {
            console.error("Failed to send message", err);
            // TODO: Show error message to user
        } finally {
            setSending(false);
        }
    };

    // ========================================================================
    // UI Render
    // ========================================================================
    return (
        <section className="h-full w-full p-6 flex flex-col items-center justify-center bg-slate-50/50">
            <div className="h-full w-full max-w-5xl flex flex-col bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden backdrop-blur-sm relative">

                {/* ============================================================
                    HEADER - Chatbot name and online status
                    ============================================================ */}
                <div className="px-6 py-4 border-b border-slate-50 flex items-center justify-between bg-white/80 backdrop-blur-md flex-none z-10">
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <div className="w-2.5 h-2.5 bg-green-500 rounded-full ring-4 ring-green-100 animate-pulse"></div>
                        </div>
                        <div>
                            <h2 className="font-bold text-slate-800 text-sm">{botName || `Chatbot #${chatbotId}`}</h2>
                            <p className="text-[10px] text-slate-400 font-medium">Online</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-50 text-slate-400 hover:text-slate-600 transition-all">
                            <MoreHorizontal size={20} />
                        </button>
                    </div>
                </div>

                {/* ============================================================
                    MESSAGES AREA - Scrollable chat history
                    Shows user and bot messages with options
                    ============================================================ */}
                <div className="flex-1 overflow-y-auto p-8 pt-6 space-y-6 bg-gradient-to-b from-white to-slate-50/30 scroll-smooth relative">

                    {/* Loading State - Shown during initial session creation */}
                    {loading && (
                        <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400 animate-pulse">
                            <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center">
                                <Bot size={20} />
                            </div>
                            <span className="text-sm font-medium">Connecting to AI...</span>
                        </div>
                    )}

                    {/* Message List - Each message with options and trigger nodes */}
                    {!loading && messages.map((msg, index) => (
                        <React.Fragment key={index}>
                            {/* Individual Message Bubble */}
                            <div className={`flex gap-4 group ${msg.sender === 'user' ? 'justify-end' : ''} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                                
                                {/* Bot Avatar - Only for bot messages */}
                                {msg.sender === 'bot' && (
                                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-100 to-white border border-slate-100 flex items-center justify-center flex-none text-slate-600 shadow-sm mt-1">
                                        <Bot size={18} />
                                    </div>
                                )}

                                {/* Message Content and Options */}
                                <div className={`flex flex-col gap-2 max-w-[70%] ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                                    
                                    {/* Message Text */}
                                    {msg.text && (
                                        <div className={`px-5 py-3.5 text-sm leading-relaxed shadow-sm ${msg.sender === 'user'
                                            ? 'bg-primary-50 border border-primary-100 text-slate-900 rounded-2xl rounded-tr-sm shadow-primary-50'
                                            : 'bg-white border border-slate-100 text-slate-700 rounded-2xl rounded-tl-sm shadow-slate-100'
                                            }`}>
                                            {msg.text}
                                        </div>
                                    )}

                                    {/* Conversation Options - Clickable buttons for next steps */}
                                    {msg.sender === 'bot' && msg.options && (
                                        <div className="flex flex-wrap gap-2 mt-1">
                                            {msg.options.map((option, idx) => (
                                                <button
                                                    key={idx}
                                                    onClick={() => handleSendMessage(option.text)}
                                                    disabled={sending}
                                                    className="px-4 py-2 bg-white border border-slate-200 text-primary-600 text-sm font-medium rounded-full hover:bg-primary-50 hover:border-primary-200 hover:shadow-md hover:-translate-y-0.5 transition-all shadow-sm disabled:opacity-50 disabled:hover:translate-y-0"
                                                    aria-label={`Select option: ${option.text}`}
                                                >
                                                    {option.text}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {/* User Avatar - Only for user messages */}
                                {msg.sender === 'user' && (
                                    <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center flex-none text-primary-700 font-bold text-xs ring-4 ring-primary-50 shadow-sm mt-1">
                                        ME
                                    </div>
                                )}
                            </div>

                            {/* Trigger Nodes - Shown after first bot message (greeting) */}
                            {/* These are workflow entry points for starting specific conversations */}
                            {index === 0 && triggerNodes.length > 0 && (
                                <div className="flex flex-col gap-2 ml-14 mb-2 animate-in fade-in slide-in-from-left-2 duration-500">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-1">Start a Workflow:</span>
                                    <div className="flex flex-wrap gap-2">
                                        {triggerNodes.map(node => (
                                            <button
                                                key={node.id}
                                                onClick={() => handleSendMessage(node.text)}
                                                disabled={sending}
                                                className="px-3 py-1.5 bg-white text-primary-700 hover:bg-primary-50 hover:text-primary-800 border border-slate-200 hover:border-primary-200 rounded-lg text-xs font-bold transition-all shadow-sm flex items-center gap-1 group/btn"
                                                aria-label={`Start workflow: ${node.text}`}
                                            >
                                                {node.text}
                                                <div className="w-1.5 h-1.5 bg-primary-400 rounded-full group-hover/btn:scale-125 transition-transform" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </React.Fragment>
                    ))}
                    
                    {/* Scroll anchor - Used by scrollToBottom() */}
                    <div ref={messagesEndRef} />
                </div>

                {/* ============================================================
                    INPUT AREA - FAQs and message input
                    ============================================================ */}
                <div className="bg-white border-t border-slate-50 flex-none p-6">

                    {/* FAQ Suggestions - Quick-access parent FAQs */}
                    <div className="mb-4">
                        <div className="flex items-center gap-2 mb-3 ml-1">
                            <div className="w-1 h-1 bg-slate-400 rounded-full"></div>
                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Frequently Asked Questions</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {/* Display actual FAQs or fallback examples */}
                            {(faqs.length > 0 ? faqs : [{ id: 0, question: 'Pricing' }, { id: 1, question: 'Support' }]).slice(0, 5).map((faq, i) => (
                                <button
                                    key={faq.id}
                                    onClick={() => handleSendMessage(faq.question)}
                                    disabled={sending}
                                    className="px-3 py-1.5 bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-slate-100 rounded-lg text-xs font-medium transition-all duration-200"
                                    aria-label={`Ask: ${faq.question}`}
                                >
                                    {faq.question}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Message Input Field and Send Button */}
                    <div className="relative flex items-center group">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                            placeholder="Ask anything..."
                            disabled={sending || !sessionId}
                            className="w-full pl-6 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-primary-400 transition-all hover:bg-white hover:shadow-md disabled:bg-slate-50 shadow-sm"
                            aria-label="Type your message"
                        />
                        <button
                            onClick={() => handleSendMessage()}
                            disabled={sending || !sessionId}
                            className={`absolute right-2 top-2 bottom-2 w-10 rounded-xl flex items-center justify-center shadow-md transition-all duration-200 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 disabled:shadow-none ${inputValue ? 'bg-black text-white shadow-slate-400' : 'bg-slate-200 text-slate-400'}`}
                            aria-label="Send message"
                        >
                            <Send size={18} className={`${sending ? 'animate-ping' : ''}`} />
                        </button>
                    </div>
                    
                    {/* Disclaimer */}
                    <div className="text-center mt-3">
                        <p className="text-[10px] text-slate-300">AI can make mistakes. Please verify important information.</p>
                    </div>
                </div>

            </div>
        </section>
    );
}
