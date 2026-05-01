"use client";
import { useState, useEffect, useRef } from 'react';
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
  X,
  Settings,
  Info,
  ShieldCheck,
  Network,
  Eye
} from 'lucide-react';

const GraphView = dynamic(() => import('@/components/graph/GraphView'), { ssr: false });

interface Message {
  id: string;
  role: 'user' | 'astra';
  content: string;
  type?: 'text' | 'analysis';
  retrievedNodes?: string[];
  isMemoryAccessed?: boolean;
}

export default function Home() {
  const [topic, setTopic] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }
  ]);
  const [loading, setLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [logs, setLogs] = useState<string[]>([
    "[SYSTEM]: Astra Engine Initialized...",
    "[SYSTEM]: Ready for command input."
  ]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isGraphVisible, setIsGraphVisible] = useState(false);
  const [expandedPanel, setExpandedPanel] = useState<'logs' | 'strategy' | 'graph' | null>(null);
  const [openContextId, setOpenContextId] = useState<string | null>(null);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const strategyEndRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
    strategyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToChatBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    scrollToChatBottom();
  }, [messages]);

  const handleAnalyze = async () => {
    if (!topic) return;
    
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
        },
        body: JSON.stringify({
          topic: currentTopic,
          history: messages.map(m => ({ role: m.role, content: m.content }))
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
              // Only turn off warm-up state when actual research content arrives
              if (data.partial_result || (data.result && data.result.trim() !== '')) {
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
                const astraMessage: Message = { 
                  id: (Date.now() + 1).toString(), 
                  role: 'astra', 
                  content: data.result,
                  type: 'analysis',
                  retrievedNodes: currentRetrievedNodes.length > 0 ? currentRetrievedNodes : undefined,
                  isMemoryAccessed: memoryAccessed
                };
                setMessages(prev => [...prev, astraMessage]);
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
              // Update the last message with partial result
              setMessages(prev => {
                const lastMessage = prev[prev.length - 1];
                if (lastMessage && lastMessage.role === 'astra' && lastMessage.type === 'analysis') {
                  return [
                    ...prev.slice(0, -1),
                    { ...lastMessage, content: data.partial_result }
                  ];
                }
                return prev;
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

      {/* Sidebar - Terminal Logs (40% width) */}
      <AnimatePresence initial={false}>
        {isSidebarOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: "40%", opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="border-l border-zinc-800/50 bg-zinc-950/40 backdrop-blur-xl flex flex-col overflow-hidden z-10 order-2"
          >
            <div className="p-4 border-b border-zinc-800/50 flex justify-between items-center bg-black/20">
              <span className="text-cyan-400 font-bold tracking-tighter text-sm flex items-center gap-2">
                <Database size={16} /> ENGINE_INSIGHTS
              </span>
              <div className="flex items-center gap-4">
                <button onClick={() => setIsSidebarOpen(false)} className="text-zinc-500 hover:text-white">
                  <ChevronRight size={20} />
                </button>
              </div>
            </div>

            {/* Logs Area (Stacked) */}
            <div className="flex-1 flex flex-col min-h-0 relative border-b border-zinc-900/50 overflow-hidden">
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

            {/* Agentic Orchestration Trace (Stacked) */}
            <div className="h-[35%] min-h-[250px] p-4 bg-zinc-950/20 flex flex-col border-t border-zinc-900/50 font-mono relative overflow-hidden">
              {/* Scanline Overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] z-10 opacity-30" />
              
              <div className="flex items-center justify-between mb-4 relative z-20 bg-black/40 backdrop-blur-md p-2 rounded-lg border border-white/5">
                <div className="flex items-center gap-2">
                  <Zap size={14} className="text-zinc-500" />
                  <span className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] font-bold">Agentic_Orchestration_Trace</span>
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
                    
                    <AnimatePresence>
                      {showClearConfirm && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9, x: -10 }}
                          animate={{ opacity: 1, scale: 1, x: 0 }}
                          exit={{ opacity: 0, scale: 0.9, x: -10 }}
                          className="absolute bottom-full right-0 mb-2 w-48 bg-zinc-900 border border-zinc-800 rounded-xl p-3 shadow-2xl z-50"
                        >
                          <p className="text-[10px] text-zinc-400 uppercase tracking-tight mb-2">Clear all neural memory?</p>
                          <div className="flex gap-2">
                            <button 
                              onClick={handleClearMemory}
                              className="flex-1 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 text-[9px] font-bold uppercase rounded transition-all"
                            >
                              Confirm
                            </button>
                            <button 
                              onClick={() => setShowClearConfirm(false)}
                              className="flex-1 py-1 bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-500 text-[9px] font-bold uppercase rounded transition-all"
                            >
                              Cancel
                            </button>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <button 
                    onClick={() => setExpandedPanel('strategy')}
                    className="p-1 hover:bg-zinc-800 rounded transition-colors"
                  >
                    <Maximize2 size={12} className="text-zinc-500 hover:text-white" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto space-y-3 custom-scrollbar relative z-20">
                {logs.filter(log => 
                  log.toLowerCase().includes("thought:") || 
                  log.toLowerCase().includes("action:") ||
                  log.toLowerCase().includes("reasoning:")
                ).map((log, i) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    key={i} 
                    className="group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`mt-1.5 w-1 h-1 rounded-full ${log.toLowerCase().includes("thought") ? "bg-amber-500" : "bg-cyan-500"}`} />
                      <div className="flex-1">
                        <div className={`text-[10px] uppercase tracking-widest mb-1 ${log.toLowerCase().includes("thought") ? "text-amber-500/50" : "text-cyan-500/50"}`}>
                          {log.toLowerCase().includes("thought") ? "Agent_Thought" : "Agent_Action"}
                        </div>
                        <div 
                          className="text-[11px] text-zinc-300 leading-relaxed italic border-l border-zinc-800/50 pl-3 whitespace-pre-wrap"
                          style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace" }}
                        >
                          <Ansi>{cleanText(log.split(/thought:|action:|reasoning:/i)[1]?.trim() || log)}</Ansi>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
                <div ref={strategyEndRef} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area (60% width) */}
      <div className={`flex-1 flex flex-col relative z-10 transition-all duration-500 ${isSidebarOpen ? 'w-[60%]' : 'w-full'}`}>
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="absolute right-4 top-24 z-20 bg-zinc-900/60 backdrop-blur-xl border border-white/10 p-3 rounded-2xl text-zinc-400 hover:text-white hover:border-cyan-500/50 transition-all shadow-2xl group"
          >
            <ChevronLeft size={20} className="group-hover:scale-110 transition-transform" />
          </button>
        )}

        {/* Chat Header */}
        <header 
          className="p-6 border-b border-cyan-500/30 flex justify-between items-center bg-[#0a0a0a] relative z-30"
        >
          <div className="flex-1">
            <button
              onClick={() => setIsAboutOpen(true)}
              className="px-4 py-1.5 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-zinc-400 hover:text-cyan-400 hover:border-cyan-500/50 hover:bg-cyan-500/10 transition-all uppercase tracking-widest flex items-center gap-2 group"
            >
              <Info size={14} className="group-hover:rotate-12 transition-transform" />
              About_Astra
            </button>
          </div>
          <div className="text-center flex-1">
            <h1 className="text-2xl font-[600] tracking-tighter text-cyan-400 font-sans" style={{ fontFamily: "'Inter', sans-serif" }}>ASTRA INTELLIGENCE</h1>
            <p className="text-[10px] text-zinc-600 uppercase tracking-[0.3em] mt-1 font-sans" style={{ fontFamily: "'Inter', sans-serif" }}>Advanced Agentic Research Framework</p>
          </div>
          <div className="flex-1 flex justify-end gap-3">
            <button
              onClick={() => setIsGraphVisible(!isGraphVisible)}
              className={`p-2 rounded-full border transition-all ${
                isGraphVisible 
                  ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.3)]' 
                  : 'bg-zinc-900/50 border-zinc-800 text-zinc-500 hover:text-white'
              }`}
              title="Toggle Knowledge Graph PiP"
            >
              <Cpu size={20} />
            </button>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar scroll-smooth bg-transparent relative">
          <AnimatePresence>
            {/* RAG Source Feed PiP Window */}
            {isGraphVisible && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8, y: 20 }}
                className="fixed bottom-32 right-8 w-[450px] h-[350px] bg-zinc-950/60 backdrop-blur-2xl border border-white/10 rounded-3xl overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 group"
              >
                <div className="p-3 border-b border-white/5 flex justify-between items-center bg-white/5 backdrop-blur-md">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-bold">RAG_Source_Feed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => setExpandedPanel('graph')}
                      className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
                      title="Fullscreen"
                    >
                      <Maximize2 size={12} className="text-zinc-500 hover:text-white" />
                    </button>
                    <button 
                      onClick={() => setIsGraphVisible(false)}
                      className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
                    >
                      <X size={12} className="text-zinc-500 hover:text-white" />
                    </button>
                  </div>
                </div>
                <div className="w-full h-full p-4 overflow-y-auto custom-scrollbar">
                  <div className="space-y-3">
                    <div className="text-xs text-emerald-400 font-bold uppercase tracking-wider mb-2">Retrieved Context</div>
                    <div className="space-y-2">
                      <div className="p-2 bg-emerald-950/20 border border-emerald-500/20 rounded-lg">
                        <div className="text-xs text-emerald-300 font-mono">🔍 Tavily Search</div>
                        <div className="text-[10px] text-zinc-400 mt-1">Real-time web sources fetched</div>
                        <div className="text-[9px] text-emerald-400/60 mt-1">• Multiple authoritative sources</div>
                      </div>
                      <div className="p-2 bg-purple-950/20 border border-purple-500/20 rounded-lg">
                        <div className="text-xs text-purple-300 font-mono">🧠 Neo4j Memory</div>
                        <div className="text-[10px] text-zinc-400 mt-1">Persistent knowledge retrieval</div>
                        <div className="text-[9px] text-purple-400/60 mt-1">• Agent state management</div>
                      </div>
                    </div>
                    <div className="text-xs text-zinc-500 mt-4">
                      <div className="font-bold text-cyan-400">RAG Pipeline Active</div>
                      <div className="mt-1 space-y-1">
                        <div>• Context Injection: ENABLED</div>
                        <div>• Source Attribution: TRACKED</div>
                        <div>• Memory Retrieval: ACTIVE</div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[85%] flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                    msg.role === 'user' ? 'bg-zinc-900 border-zinc-700 text-zinc-400' : 'bg-cyan-950/30 border-cyan-500/30 text-cyan-400'
                  }`}>
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>
                  
                  <div className={`space-y-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                      {msg.role === 'user' ? 'Operator' : 'Astra_Engine'}
                      {msg.isMemoryAccessed && (
                        <div className="flex items-center gap-1 group relative">
                          <span className="flex items-center gap-1 text-purple-400 bg-purple-400/10 px-1.5 py-0.5 rounded border border-purple-400/20 lowercase animate-pulse">
                            <Brain size={10} className="text-purple-300" /> neural_memory_active
                          </span>
                          <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block w-48 p-2 bg-zinc-900 border border-zinc-800 rounded text-[9px] text-zinc-300 normal-case shadow-2xl z-50">
                            Information retrieved from Astra&apos;s persistent Knowledge Graph
                          </div>
                        </div>
                      )}
                      {msg.retrievedNodes && !msg.isMemoryAccessed && (
                        <span className="flex items-center gap-1 text-purple-400 bg-purple-400/10 px-1.5 py-0.5 rounded border border-purple-400/20 lowercase">
                          <Database size={10} /> memory_sourced
                        </span>
                      )}
                    </div>
                    {msg.type === 'analysis' ? (
                      <div className="w-full space-y-4 max-w-full overflow-hidden">
                        <AnalysisDisplay 
                          result={msg.content}
                          status="completed"
                          currentNode="end"
                          message="Analysis complete"
                        />
                        
                        {msg.retrievedNodes && (
                          <div className="mt-2">
                            <button 
                              onClick={() => setOpenContextId(openContextId === msg.id ? null : msg.id)}
                              className="text-[10px] text-zinc-500 hover:text-cyan-400 uppercase tracking-widest flex items-center gap-2 transition-colors mb-2"
                            >
                              {openContextId === msg.id ? <ChevronLeft size={12} className="rotate-90" /> : <ChevronRight size={12} />}
                              Context_Window ({msg.retrievedNodes.length} nodes)
                            </button>
                            
                            <AnimatePresence>
                              {openContextId === msg.id && (
                                <motion.div 
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: "auto", opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="overflow-hidden"
                                >
                                  <div className="bg-zinc-950 border border-zinc-900 rounded-xl p-4 flex flex-wrap gap-2">
                                    {msg.retrievedNodes.map((node, i) => (
                                      <span key={i} className="text-[10px] bg-zinc-900 border border-zinc-800 text-cyan-400/80 px-2 py-1 rounded-md">
                                        {node}
                                      </span>
                                    ))}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div 
                        className={`p-4 rounded-2xl text-sm leading-relaxed border backdrop-blur-md transition-all ${
                          msg.role === 'user' 
                            ? 'bg-zinc-900/40 border-zinc-800 text-zinc-200 rounded-tr-none' 
                            : 'bg-cyan-950/20 border-cyan-500/20 text-cyan-50 rounded-tl-none shadow-[0_4px_20px_rgba(0,0,0,0.3)]'
                        }`}
                        style={{ 
                          fontFamily: "'Inter', sans-serif"
                        }}
                      >
                        {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Gemini-style 'Astra Pulse' Loader */}
          <AnimatePresence>
            {isWarmingUp && loading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex justify-start"
              >
                <div className="max-w-[85%] flex gap-4">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border bg-cyan-950/30 border-cyan-500/30 text-cyan-400">
                    <Bot size={16} />
                  </div>
                  
                  <div className="space-y-2 text-left">
                    <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                      Astra_Engine
                      <span className="flex items-center gap-1 text-cyan-400 bg-cyan-400/10 px-1.5 py-0.5 rounded border border-cyan-400/20 lowercase animate-pulse">
                        <Activity size={10} className="text-cyan-300" /> thinking
                      </span>
                    </div>
                    
                    <div className="p-4 rounded-2xl text-sm leading-relaxed border backdrop-blur-md bg-cyan-950/20 border-cyan-500/20 text-cyan-50 rounded-tl-none shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
                      <div className="flex items-center gap-2">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-cyan-300 text-sm">Initializing research sequence...</span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-8 bg-gradient-to-t from-[#050505] via-[#050505]/80 to-transparent relative z-20">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute inset-0 bg-cyan-500/10 blur-2xl rounded-[32px] opacity-0 group-focus-within:opacity-100 transition-opacity duration-700" />
            <div className="relative flex items-center gap-4 bg-white/[0.03] backdrop-blur-2xl border border-white/10 p-2 pl-6 rounded-[24px] focus-within:border-cyan-500/40 focus-within:bg-white/[0.05] transition-all duration-300 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
              <input
                className="flex-1 bg-transparent border-none py-4 text-sm text-white placeholder-zinc-500 focus:outline-none font-medium"
                placeholder="Initialize research sequence..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !loading && handleAnalyze()}
              />
              <button
                onClick={handleAnalyze}
                disabled={loading || !topic}
                className={`px-6 py-3 rounded-[18px] transition-all flex items-center justify-center font-bold tracking-tighter uppercase text-xs border border-cyan-500/30 ${
                  loading || !topic 
                    ? 'bg-zinc-800/50 text-zinc-600 cursor-not-allowed' 
                    : 'bg-[#0a0a0a] text-cyan-400 hover:bg-[#111] hover:scale-[1.02] active:scale-[0.98]'
                }`}
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                ) : (
                  <span className="flex items-center gap-2">Execute <Send size={14} /></span>
                )}
              </button>
            </div>
            
            {/* Professional Loading State - Warm-up Phase */}
            <AnimatePresence>
              {isWarmingUp && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mt-6 p-4 bg-cyan-950/10 border border-cyan-500/20 rounded-2xl backdrop-blur-md"
                >
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse" />
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse delay-75" />
                    <div className="w-3 h-3 bg-cyan-400 rounded-full animate-pulse delay-150" />
                    <span className="text-cyan-300 text-sm font-medium ml-2">
                      Astra is warming up... Initializing research engine
                    </span>
                  </div>
                  <div className="mt-2 text-center text-xs text-cyan-400/60">
                    Preparing GLM-5.1 for deep analysis
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            
            <div className="mt-4 flex justify-center gap-8 text-[9px] uppercase tracking-[0.25em] text-zinc-500 font-bold opacity-50">
              <span className="flex items-center gap-2 hover:text-emerald-400 transition-colors"><div className="w-1 h-1 rounded-full bg-emerald-500" /> GLM-5.1_Model</span>
              <span className="flex items-center gap-2 hover:text-cyan-400 transition-colors"><div className="w-1 h-1 rounded-full bg-cyan-500" /> Multi-Agent_Orchestration</span>
              <span className="flex items-center gap-2 hover:text-amber-400 transition-colors"><div className="w-1 h-1 rounded-full bg-amber-500" /> RAG_Pipeline_Active</span>
              <span className="flex items-center gap-2 hover:text-purple-400 transition-colors"><div className="w-1 h-1 rounded-full bg-purple-500" /> Latency: <span id="latency-metric">~300ms</span></span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}