"use client";
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import AnalysisDisplay from '@/components/AnalysisDisplay';
import Ansi from 'ansi-to-react';
import { BACKEND_URL } from '@/lib/api';
import {
  Terminal,
  Database,
  Send,
  ChevronRight,
  ChevronLeft,
  Bot,
  User,
  Cpu,
  Brain,
  Zap,
  Activity,
  Maximize2,
  Plus,
  MessageSquare,
  Info,
  X,
  Settings,
  ShieldCheck,
  Network,
  Eye,
  Menu,
  Paperclip,
  BookOpen
} from 'lucide-react';

const GraphView = dynamic(() => import('@/components/graph/GraphView'), { ssr: false });

import { Message } from '@/types';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import ChatInput from '@/components/chat/ChatInput';
import MessageList from '@/components/chat/MessageList';
import { v4 as uuidv4 } from 'uuid';
import { supabase } from '@/lib/supabase';

export default function Home() {
  const [topic, setTopic] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }
  ]);
  const [loading, setLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [ragMode, setRagMode] = useState<"general" | "strict_local">("general");
  const [currentChatId, setCurrentChatId] = useState<string>("");
  const [userId, setUserId] = useState<string | null>(null);

  // Fetch current user on mount
  useEffect(() => {
    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setUserId(session.user.id);
      }
    };
    getUser();
  }, []);

  useEffect(() => {
    setCurrentChatId(uuidv4());
  }, []);

  // Auto-save chat history to Supabase
  useEffect(() => {
    if (!currentChatId || messages.length <= 1) return;
    
    const saveChat = async () => {
      try {
        const firstUserMsg = messages.find(m => m.role === 'user');
        const chatTitle = firstUserMsg ? firstUserMsg.content.substring(0, 40) + (firstUserMsg.content.length > 40 ? '...' : '') : 'New Research';
        
        await supabase
        .from('chats')
        .upsert({
          id: currentChatId,
          title: chatTitle,
          messages: messages,
          updated_at: new Date().toISOString(),
          user_id: userId
        }, { onConflict: 'id' });
      } catch (e) {
        console.error("Failed to save chat:", e);
      }
    };

    const timeoutId = setTimeout(saveChat, 1500);
    return () => clearTimeout(timeoutId);
  }, [messages, currentChatId, userId]);

  const loadChat = async (chatId: string) => {
    try {
      const { data, error } = await supabase
        .from('chats')
        .select('*')
        .eq('id', chatId)
        .single();
        
      if (error) throw error;
      if (data) {
        setCurrentChatId(data.id);
        setMessages(data.messages);
        setTopic("");
        setLogs([]);
        setLoading(false);
        setIsWarmingUp(false);
        setActiveAgent(null);
        if (isMobileNavOpen) setIsMobileNavOpen(false);
      }
    } catch (err) {
      console.error("Failed to load chat", err);
      showToast("Failed to load chat history");
    }
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${BACKEND_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      if (response.ok) {
        setRagMode("strict_local");
      } else {
        setToast(`Error: ${data.detail || 'Upload failed'}`);
      }
    } catch (err) {
      setToast('Upload failed to connect to backend.');
    } finally {
      setLoading(false);
      setTimeout(() => setToast(null), 3000);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };
  const [logs, setLogs] = useState<string[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isGraphVisible, setIsGraphVisible] = useState(false);
  const [expandedPanel, setExpandedPanel] = useState<'logs' | 'strategy' | 'graph' | null>(null);
  const [openContextId, setOpenContextId] = useState<string | null>(null);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const strategyEndRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isAutoScrollPausedRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    strategyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const scrollToChatBottom = useCallback(() => {
    if (isAutoScrollPausedRef.current) return;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    
    // Check if user is near the bottom (within a 100px buffer)
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    if (isAtBottom) {
      isAutoScrollPausedRef.current = false;
    } else {
      // Only pause if currently loading/streaming content
      if (loading) {
        isAutoScrollPausedRef.current = true;
      }
    }
  };

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    scrollToChatBottom();
  }, [messages]);

  // Auto-scroll during research generation
  useEffect(() => {
    if (loading && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage && lastMessage.role === 'astra' && lastMessage.type === 'analysis') {
        scrollToChatBottom();
      }
    }
  }, [messages, loading]);

  // Enhanced auto-scroll during loading state
  useEffect(() => {
    if (loading) {
      const scrollInterval = setInterval(() => {
        scrollToChatBottom();
      }, 500); // Scroll every 500ms during loading

      return () => clearInterval(scrollInterval);
    }
  }, [loading]);

  const handleAnalyze = async () => {
    if (!topic) return;
    
    isAutoScrollPausedRef.current = false; // Reset scroll hold for new query
    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: topic };
    setMessages(prev => [...prev, userMessage]);
    const currentTopic = topic;
    setTopic("");
    setLoading(true);
    setIsWarmingUp(true); // Trigger warm-up state immediately
    
    let currentRetrievedNodes: string[] = [];
    let memoryAccessed = false;
    setLogs(prev => [...prev, `[USER]: Start analysis for "${currentTopic}"`]);
    
    try {
      const response = await fetch(`${BACKEND_URL}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userId && { "Authorization": `Bearer ${userId}` })
        },
        body: JSON.stringify({
          topic: currentTopic,
          history: messages.map(m => ({ role: m.role, content: m.content })),
          rag_mode: ragMode,
          user_id: userId
        }),
      });

      if (!response.body) throw new Error('No response body');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.replace('data: ', ''));
            
            // Handle LangGraph status events
            if (data.status) {
              // Only turn off warm-up state when research is truly complete
              if (data.status === 'completed' && data.result && data.result.trim() !== '') {
                setIsWarmingUp(false);
              }
              setLogs(prev => [...prev, `[${data.node?.toUpperCase() || 'SYSTEM'}]: ${data.message}`]);
              
              // Update active agent based on node
              if (data.node === 'researcher') setActiveAgent("Researcher");
              else if (data.node === 'critic') setActiveAgent("Critic");
              else if (data.node === 'storage') setActiveAgent("Storage");
              else if (data.node === 'end') setActiveAgent(null);
              
              // Handle completion
              if (data.status === 'completed' && data.result) {
                setMessages(prev => {
                  const lastMessage = prev[prev.length - 1];
                  if (lastMessage && lastMessage.role === 'astra' && lastMessage.type === 'analysis') {
                    return [...prev.slice(0, -1), { ...lastMessage, content: data.result, retrievedNodes: currentRetrievedNodes.length > 0 ? currentRetrievedNodes : undefined, isMemoryAccessed: memoryAccessed }];
                  }
                  return [...prev, { id: (Date.now() + 1).toString(), role: 'astra', content: data.result, type: 'analysis', retrievedNodes: currentRetrievedNodes.length > 0 ? currentRetrievedNodes : undefined, isMemoryAccessed: memoryAccessed }];
                });
                setActiveAgent(null);
                setLogs(prev => [...prev, "[SYSTEM]: Analysis sequence complete."]);
                setLoading(false);
              }
              
              // Handle errors
              if (data.status === 'error') {
                setLogs(prev => [...prev, `[ERROR]: ${data.message}`]);
                const errorMessage: Message = { 
                  id: (Date.now() + 1).toString(), 
                  role: 'astra', 
                  content: `Error: ${data.message}` 
                };
                setMessages(prev => [...prev, errorMessage]);
                setLoading(false);
              }
            }
            // Handle partial results during streaming
            else if (data.partial_result) {
              setMessages(prev => {
                const lastMessage = prev[prev.length - 1];
                if (lastMessage && lastMessage.role === 'astra' && lastMessage.type === 'analysis') {
                  // Append the token to the existing stream
                  return [
                    ...prev.slice(0, -1),
                    { ...lastMessage, content: lastMessage.content + data.partial_result }
                  ];
                } else {
                  // Create the initial stream message
                  return [
                    ...prev,
                    { id: Date.now().toString(), role: 'astra', content: data.partial_result, type: 'analysis', isMemoryAccessed: memoryAccessed }
                  ];
                }
              });
            }
            // Legacy support for old format
            else if (data.type === 'log') {
              const content = data.content;
              setLogs(prev => [...prev, content]);
              
              // Extract nodes from retrieval logs
              if (content.includes("Existing Knowledge Found")) {
                memoryAccessed = true;
                const nodeMatches = content.match(/\[(.*?)\]/g);
                if (nodeMatches) {
                  const nodes = nodeMatches.map((m: string) => m.slice(1, -1));
                  currentRetrievedNodes = Array.from(new Set([...currentRetrievedNodes, ...nodes]));
                }
              }

              if (content.includes("Found the following in my memory:")) {
                memoryAccessed = true;
              }

              if (content.includes("Researcher")) setActiveAgent("Researcher");
              else if (content.includes("Critic")) setActiveAgent("Critic");
              else if (content.includes("Final Answer")) setActiveAgent(null);
            } else if (data.type === 'result') {
              const astraMessage: Message = { 
                id: (Date.now() + 1).toString(), 
                role: 'astra', 
                content: data.content,
                type: 'analysis',
                retrievedNodes: currentRetrievedNodes.length > 0 ? currentRetrievedNodes : undefined,
                isMemoryAccessed: memoryAccessed
              };
              setMessages(prev => [...prev, astraMessage]);
              setActiveAgent(null);
              setLogs(prev => [...prev, "[SYSTEM]: Analysis sequence complete. Compiling report..."]);
              setLoading(false);
            } else if (data.type === 'error') {
              setLogs(prev => [...prev, `[ERROR]: ${data.content}`]);
              const errorMessage: Message = { 
                id: (Date.now() + 1).toString(), 
                role: 'astra', 
                content: `Error: ${data.content}` 
              };
              setMessages(prev => [...prev, errorMessage]);
              setLoading(false);
            }
          }
        }
      }
    } catch (error) {
      setLogs(prev => [...prev, `[ERROR]: Connection failed`]);
      setLoading(false);
    }
  };

  const getLogColor = (log: string) => {
    if (log.includes("[SYSTEM]")) return "text-cyan-400";
    if (log.includes("[USER]")) return "text-white";
    if (log.includes("[ERROR]")) return "text-red-500";
    if (log.includes("retrieve_knowledge_tool") || log.includes("Existing Knowledge Found")) return "text-purple-400 font-bold";
    if (log.includes("Researcher")) return "text-emerald-400";
    if (log.includes("Critic")) return "text-amber-400";
    return "text-zinc-400";
  };

  const cleanText = (text: string) => {
    return text
      .replace(/\|{2,}/g, '|') // Replace multiple pipes with a single pipe
      .replace(/_{2,}/g, '_')   // Replace multiple underscores with a single underscore
      .trim();
  };

  const PulseIcon = () => (
    <motion.div
      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
      transition={{ duration: 1, repeat: Infinity }}
      className="w-2 h-2 bg-red-500 rounded-full inline-block ml-2"
    />
  );

  const handleClearMemory = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/clear_graph`, { method: "POST" });
      const data = await response.json();
      setLogs(prev => [...prev, `[SYSTEM]: ${data.message}`]);
      setShowClearConfirm(false);
    } catch (error) {
      setLogs(prev => [...prev, "[ERROR]: Clear request failed"]);
    }
  };

  return (
    <main className="flex h-screen bg-[#050505] text-zinc-100 selection:bg-cyan-500/30 overflow-hidden relative">
      {/* About Modal */}
      <AnimatePresence>
        {isAboutOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsAboutOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-2xl bg-zinc-950 border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.8)] z-10"
            >
              <div className="p-8 space-y-8">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-3xl font-bold tracking-tighter text-cyan-400">ASTRA</h2>
                    <p className="text-zinc-400 mt-2 leading-relaxed max-w-md">
                      Astra is an Advanced Agentic Research Framework utilizing GraphRAG and Multi-Agent Orchestration.
                    </p>
                  </div>
                  <button 
                    onClick={() => setIsAboutOpen(false)}
                    className="p-2 hover:bg-white/5 rounded-full transition-colors"
                  >
                    <X size={20} className="text-zinc-500 hover:text-white" />
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-6">
                  <div className="space-y-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                      <ShieldCheck size={20} className="text-emerald-400" />
                    </div>
                    <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Intelligence</h3>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      Multi-agent collaboration with Llama 3.3.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                      <Network size={20} className="text-purple-400" />
                    </div>
                    <h3 className="text-sm font-bold text-purple-400 uppercase tracking-wider">Memory</h3>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      Persistent Knowledge Graph using Neo4j.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                      <Eye size={20} className="text-cyan-400" />
                    </div>
                    <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider">Observability</h3>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      Real-time thought streaming and strategy visualization.
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white/5 border-t border-white/5 px-8 py-4 flex justify-between items-center text-[10px] text-zinc-500 uppercase tracking-widest font-mono">
                <span>Astra_v1.0.4</span>
                <span>System_Stable</span>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Background Decorative Elements */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(20,20,20,1)_0%,rgba(0,0,0,1)_100%)] z-0" />
      <div className="absolute inset-0 opacity-20 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] pointer-events-none z-0" />
      
      {/* Fullscreen Modal Overlay */}
      <AnimatePresence>
        {expandedPanel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-xl flex items-center justify-center p-8"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full h-full bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden flex flex-col shadow-2xl"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-6 border-b border-zinc-900 bg-black/50">
                <div className="flex items-center gap-3">
                  {expandedPanel === 'logs' && <Terminal className="text-zinc-400" />}
                  {expandedPanel === 'strategy' && <Activity className="text-amber-500" />}
                  {expandedPanel === 'graph' && <Cpu className="text-cyan-500" />}
                  <h2 className="text-lg font-mono uppercase tracking-widest font-bold">
                    {expandedPanel === 'logs' && "Process_Logs_Detailed"}
                    {expandedPanel === 'strategy' && "Strategy_Stream_Analysis"}
                    {expandedPanel === 'graph' && "Knowledge_Graph_Full_View"}
                  </h2>
                </div>
                <button 
                  onClick={() => setExpandedPanel(null)}
                  className="p-2 hover:bg-zinc-800 rounded-full transition-all group"
                >
                  <X className="text-zinc-500 group-hover:text-white" />
                </button>
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-hidden relative">
                {expandedPanel === 'graph' ? (
                  <div className="w-full h-full p-4">
                    <GraphView />
                  </div>
                ) : (
                  <div className="w-full h-full overflow-y-auto p-8 font-mono custom-scrollbar relative">
                    {/* Scanline Overlay */}
                    <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] z-10 opacity-50" />
                    
                    <div className="relative z-20 space-y-4">
                      {(expandedPanel === 'logs' ? logs : logs.filter(l => 
                        l.toLowerCase().includes("thought:") || 
                        l.toLowerCase().includes("action:") ||
                        l.toLowerCase().includes("reasoning:")
                      )).map((log, i) => (
                        <div key={i} className={`text-sm leading-relaxed whitespace-pre-wrap ${expandedPanel === 'logs' ? getLogColor(log) : 'text-zinc-300'}`}>
                          {expandedPanel === 'logs' && <span className="opacity-30 mr-4 font-bold">[{i.toString().padStart(3, '0')}]</span>}
                          <Ansi>{expandedPanel === 'logs' ? cleanText(log) : cleanText(log.split(/thought:|action:|reasoning:/i)[1]?.trim() || log)}</Ansi>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Navigation Backdrop */}
      <AnimatePresence>
        {isMobileNavOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsMobileNavOpen(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          />
        )}
      </AnimatePresence>

      {/* Left Navigation Sidebar - Gemini Style */}
      {/* Left Navigation Sidebar - Chat History */}
      <AnimatePresence initial={false}>
        {isHistoryOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 240, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="hidden md:block h-full flex-shrink-0 overflow-hidden"
          >
            <div className="w-[240px] h-full">
              <Sidebar 
                isMobileNavOpen={false}
                setIsMobileNavOpen={setIsMobileNavOpen}
                resetChat={() => {
                  setMessages([{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }]);
                  setCurrentChatId(uuidv4());
                  setLogs([]);
                  setTopic("");
                  setLoading(false);
                  setIsWarmingUp(false);
                  setActiveAgent(null);
                }}
                loadChat={loadChat}
                currentChatId={currentChatId}
                showToast={showToast}
                isAboutOpen={isAboutOpen}
                setIsAboutOpen={setIsAboutOpen}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Mobile Sidebar */}
      <div className="md:hidden">
        <Sidebar 
          isMobileNavOpen={isMobileNavOpen}
          setIsMobileNavOpen={setIsMobileNavOpen}
          resetChat={() => {
            setMessages([{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }]);
            setCurrentChatId(uuidv4());
            setLogs([]);
            setTopic("");
            setLoading(false);
            setIsWarmingUp(false);
            setActiveAgent(null);
          }}
          loadChat={loadChat}
          currentChatId={currentChatId}
          showToast={showToast}
          isAboutOpen={isAboutOpen}
          setIsAboutOpen={setIsAboutOpen}
        />
      </div>

      {/* Main Chat Area (75% width) */}
      <div className={`flex-1 flex flex-col relative z-10 transition-all duration-500 w-full ${isSidebarOpen ? '' : ''}`}>

        <Header 
          isMobileNavOpen={isMobileNavOpen}
          setIsMobileNavOpen={setIsMobileNavOpen}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          isHistoryOpen={isHistoryOpen}
          setIsHistoryOpen={setIsHistoryOpen}
          ragMode={ragMode}
          setRagMode={setRagMode}
        />

        {/* Messages Area */}
        <MessageList 
          messages={messages}
          isWarmingUp={isWarmingUp}
          loading={loading}
          scrollContainerRef={scrollContainerRef}
          handleScroll={handleScroll}
          chatEndRef={chatEndRef}
          scrollToChatBottom={scrollToChatBottom}
        />

        {/* Input Area */}
        <ChatInput 
          loading={loading}
          topic={topic}
          setTopic={setTopic}
          handleAnalyze={handleAnalyze}
          fileInputRef={fileInputRef}
          handleFileUpload={handleFileUpload}
        />
      </div>

      {/* Right Sidebar - Terminal Logs (Engine Insights) */}
      <AnimatePresence initial={false}>
        {isSidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="hidden lg:flex border-l border-white/5 bg-zinc-950/80 backdrop-blur-3xl flex-col overflow-hidden z-10 flex-shrink-0"
          >
            <div className="p-4 border-b border-zinc-800/50 flex justify-center items-center bg-black/20">
              <span className="text-cyan-400 font-bold tracking-tighter text-sm flex items-center gap-2">
                <Database size={16} /> ENGINE_INSIGHTS
              </span>
            </div>

            {/* Section 1: RAG Source Feed (Top 50%) - SINGLE INSTANCE */}
            <div className="h-1/2 p-4 bg-zinc-950/20 flex flex-col border-t border-zinc-900/50 font-mono relative overflow-hidden">
              {/* Scanline Overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] z-10 opacity-30" />
              
              <div className="flex items-center justify-between mb-4 relative z-20 bg-black/40 backdrop-blur-md p-2 rounded-lg border border-white/5">
                <div className="flex items-center gap-2">
                  <Database size={14} className="text-emerald-500" />
                  <span className="text-[10px] text-emerald-500 uppercase tracking-[0.2em] font-bold">RAG_Source_Feed</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <button 
                      onClick={() => setShowClearConfirm(!showClearConfirm)}
                      className="p-1 hover:bg-zinc-800 rounded transition-colors group"
                      title="System Settings"
                    >
                      <Settings size={12} className={`text-zinc-500 group-hover:text-white ${showClearConfirm ? 'rotate-90 text-cyan-400' : ''} transition-transform`} />
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar relative z-20">
                <div className="space-y-4 p-2">
                  <div className="text-xs text-emerald-400 font-bold uppercase tracking-wider mb-2">Retrieved Context</div>
                  
                  {/* Tavily Search Section */}
                  <div className="p-3 bg-emerald-950/20 border border-emerald-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                      <div className="text-xs text-emerald-300 font-mono">🔍 Tavily Search</div>
                    </div>
                    <div className="text-[10px] text-zinc-400 leading-relaxed">
                      Real-time web sources fetched for current query
                    </div>
                    <div className="mt-2 space-y-1">
                      <div className="text-[9px] text-emerald-400/60">• Multiple authoritative sources</div>
                      <div className="text-[9px] text-emerald-400/60">• Current information retrieval</div>
                      <div className="text-[9px] text-emerald-400/60">• Context injection enabled</div>
                    </div>
                  </div>

                  {/* Neo4j Memory Section */}
                  <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                      <div className="text-xs text-purple-300 font-mono">🧠 Neo4j Memory</div>
                    </div>
                    <div className="text-[10px] text-zinc-400 leading-relaxed">
                      Persistent knowledge retrieval from graph database
                    </div>
                    <div className="mt-2 space-y-1">
                      <div className="text-[9px] text-purple-400/60">• Agent state management</div>
                      <div className="text-[9px] text-purple-400/60">• Historical context access</div>
                      <div className="text-[9px] text-purple-400/60">• Knowledge graph traversal</div>
                    </div>
                  </div>

                  {/* RAG Pipeline Status */}
                  <div className="mt-4 p-3 bg-cyan-950/10 border border-cyan-500/20 rounded-lg">
                    <div className="text-xs text-cyan-400 font-bold mb-2">RAG Pipeline Status</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-zinc-400">Context Injection</span>
                        <span className="text-[9px] text-emerald-400">ACTIVE</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-zinc-400">Source Attribution</span>
                        <span className="text-[9px] text-emerald-400">TRACKED</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-zinc-400">Memory Retrieval</span>
                        <span className="text-[9px] text-emerald-400">ENABLED</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div ref={strategyEndRef} />
              </div>
            </div>

            {/* Section 2: Process Logs (Bottom 50%) - FILLS REMAINING SPACE */}
            <div className="h-1/2 flex flex-col min-h-0 relative border-b border-zinc-800/50 overflow-hidden">
              {/* Scanline Overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] z-10 opacity-30" />
              
              <div className="flex items-center justify-between p-4 pb-2 relative z-20 bg-black/40 backdrop-blur-md">
                <div className="flex items-center gap-2">
                  <Terminal size={14} className="text-zinc-500" />
                  <span className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold">Process_Logs</span>
                </div>
                <button 
                  onClick={() => setExpandedPanel('logs')}
                  className="p-1 hover:bg-zinc-800 rounded transition-colors"
                >
                  <Maximize2 size={12} className="text-zinc-500 hover:text-white" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4 pt-0 space-y-2 custom-scrollbar font-mono relative z-20">
                <div className="relative">
                  {logs.map((log, i) => (
                    <motion.div 
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      key={i} 
                      className={`text-[11px] leading-relaxed break-all whitespace-pre-wrap ${getLogColor(log)}`}
                      style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
                    >
                      <span className="opacity-30 mr-2">[{i.toString().padStart(3, '0')}]</span>
                      <Ansi>{cleanText(log)}</Ansi>
                    </motion.div>
                  ))}
                </div>
                <div ref={terminalEndRef} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -50, scale: 0.9 }}
            className="fixed top-8 right-8 bg-zinc-900 border border-cyan-500/30 text-cyan-400 px-6 py-3 rounded-2xl shadow-2xl z-50 backdrop-blur-xl"
          >
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              <span className="text-sm font-medium">{toast}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}