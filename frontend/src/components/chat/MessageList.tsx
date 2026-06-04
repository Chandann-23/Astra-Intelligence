import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Bot, Brain, Database, ChevronLeft, ChevronRight, Activity } from 'lucide-react';
import AnalysisDisplay from '@/components/AnalysisDisplay';
import { Message } from '@/types';

interface MessageListProps {
  messages: Message[];
  isWarmingUp: boolean;
  loading: boolean;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  handleScroll: () => void;
  chatEndRef: React.RefObject<HTMLDivElement | null>;
  scrollToChatBottom: () => void;
}

export default function MessageList({
  messages,
  isWarmingUp,
  loading,
  scrollContainerRef,
  handleScroll,
  chatEndRef,
  scrollToChatBottom
}: MessageListProps) {
  const [openContextId, setOpenContextId] = useState<string | null>(null);

  return (
    <div 
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto p-3 md:p-6 space-y-4 md:space-y-8 custom-scrollbar scroll-smooth bg-transparent relative"
    >
      <AnimatePresence>
        {messages.map((msg, i) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[95%] md:max-w-[85%] flex gap-2 md:gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                msg.role === 'user' ? 'bg-zinc-900 border-zinc-700 text-zinc-400' : 'bg-emerald-950/20 border-emerald-500/20 text-emerald-400'
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
                        Information retrieved from Astra's persistent Knowledge Graph
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
                      status={loading && i === messages.length - 1 ? 'processing' : 'completed'}
                      currentNode="end"
                      message="Analysis complete"
                      onScroll={scrollToChatBottom}
                    />
                    
                    {msg.retrievedNodes && (
                      <div className="mt-2">
                        <button 
                          onClick={() => setOpenContextId(openContextId === msg.id ? null : msg.id)}
                          className="text-[10px] text-zinc-500 hover:text-emerald-400 uppercase tracking-widest flex items-center gap-2 transition-colors mb-2"
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
                                  <span key={i} className="text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-400 px-2 py-1 rounded-md">
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
                    className={`p-4 rounded-3xl text-sm leading-relaxed border transition-all ${
                      msg.role === 'user' 
                        ? 'bg-zinc-900/60 border-white/5 text-zinc-200 rounded-tr-sm shadow-xl' 
                        : 'bg-emerald-950/10 border-emerald-500/10 text-emerald-50 rounded-tl-sm shadow-[0_4px_30px_rgba(16,185,129,0.05)]'
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
      
      {/* Enhanced Skeleton Loader State */}
      <AnimatePresence>
        {isWarmingUp && loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex justify-start"
          >
            <div className="max-w-[95%] flex gap-4">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border bg-emerald-950/20 border-emerald-500/20 text-emerald-400">
                <Bot size={16} />
              </div>
              
              <div className="space-y-2 text-left">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
                  Astra_Engine
                  <span className="flex items-center gap-1 text-emerald-400 bg-emerald-400/10 px-1.5 py-0.5 rounded border border-emerald-400/20 lowercase animate-pulse">
                    <Activity size={10} className="text-emerald-300" /> thinking
                  </span>
                </div>
                
                <div className="p-5 rounded-3xl border backdrop-blur-md bg-emerald-950/5 border-white/5 text-emerald-50 rounded-tl-sm shadow-xl w-64">
                  <div className="space-y-3">
                    <div className="h-2 bg-emerald-500/20 rounded animate-pulse w-3/4"></div>
                    <div className="h-2 bg-emerald-500/20 rounded animate-pulse w-full"></div>
                    <div className="h-2 bg-emerald-500/20 rounded animate-pulse w-5/6"></div>
                  </div>
                  <div className="mt-4 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-ping"></div>
                    <span className="text-emerald-500/60 text-[10px] uppercase tracking-widest">Initializing...</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <div ref={chatEndRef} />
    </div>
  );
}
