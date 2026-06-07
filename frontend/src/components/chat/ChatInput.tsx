import React, { useState, useRef, useEffect } from 'react';
import { Paperclip, Send, ChevronUp, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '@/store/useChatStore';

interface ChatInputProps {
  loading: boolean;
  topic: string;
  setTopic: (v: string) => void;
  handleAnalyze: (overrideTopic?: string) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  handleFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function ChatInput({
  loading,
  topic,
  setTopic,
  handleAnalyze,
  fileInputRef,
  handleFileUpload
}: ChatInputProps) {
  const { llmProvider, setLlmProvider, developerResumeMode, setDeveloperResumeMode } = useChatStore();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const generalPrompts = [
    { text: 'Compare Neural-Symbolic AI with Deep Learning', label: 'Research' },
    { text: 'Calculate the 15th Fibonacci number in Python', label: 'Code sandbox' },
    { text: 'Analyze quantum computing developments in 2026', label: 'Web search' }
  ];

  const resumePrompts = [
    { text: 'Why should we hire Chandan for a Senior AI Dev role?', label: 'RAG pitch' },
    { text: "Describe Chandan's experience with LangGraph & agents", label: 'Core skills' },
    { text: "What are Chandan's featured software projects?", label: 'Portfolio' }
  ];

  const activePrompts = developerResumeMode ? resumePrompts : generalPrompts;

  const handlePromptClick = (promptText: string) => {
    setTopic("");
    handleAnalyze(promptText);
  };

  const models = [
    { id: 'mistral',   label: 'Mistral Small',          iconColor: 'bg-rose-500'    },
    { id: 'groq',      label: 'Groq Llama 3.3 70B',    iconColor: 'bg-orange-500'  },
    { id: 'cerebras',  label: 'Cerebras GPT-OSS 120B',  iconColor: 'bg-purple-500'  },
    { id: 'sambanova', label: 'SambaNova Llama 4',      iconColor: 'bg-blue-500'    },
    { id: 'gemini',    label: 'Gemini 2.0 Flash',      iconColor: 'bg-emerald-500' },
  ];
  
  const currentModel = models.find(m => m.id === llmProvider) || models[0];

  return (
    <div className="p-3 md:p-8 bg-gradient-to-t from-black via-black/80 to-transparent relative z-20 shrink-0">
      <div className="max-w-4xl mx-auto relative group">
        
        {/* Prompts & Toggle Header — hidden while typing or generating */}
        <AnimatePresence>
          {!topic && !loading && (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-3 px-2"
            >
              {/* Sample Prompts Pills */}
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-[9px] uppercase tracking-widest text-zinc-500 font-bold mr-1">Suggestions:</span>
                {activePrompts.map((p, idx) => (
                  <button
                    key={idx}
                    disabled={loading}
                    onClick={() => handlePromptClick(p.text)}
                    className="text-[10px] text-zinc-400 bg-white/[0.02] border border-white/5 hover:border-cyan-500/20 hover:bg-cyan-500/5 px-3 py-1 rounded-full transition-all text-left truncate max-w-[280px] sm:max-w-none disabled:opacity-50 disabled:cursor-not-allowed"
                    title={p.text}
                  >
                    <span className="font-semibold text-cyan-500 mr-1">[{p.label}]</span> {p.text}
                  </button>
                ))}
              </div>

              {/* Developer RAG Toggle */}
              <button
                onClick={() => setDeveloperResumeMode(!developerResumeMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[9px] font-bold uppercase tracking-wider transition-all self-start md:self-auto ${
                  developerResumeMode
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)] animate-pulse'
                    : 'bg-zinc-950/40 border-white/5 text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                }`}
                title="Toggle Developer Portfolio Index RAG"
              >
                🚀 Developer_RAG_Mode: {developerResumeMode ? 'ON' : 'OFF'}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="absolute inset-0 bg-emerald-500/5 blur-2xl rounded-[32px] opacity-0 group-focus-within:opacity-100 transition-opacity duration-700 pointer-events-none" />
        
        <div className="relative flex items-center gap-2 md:gap-4 bg-white/[0.02] backdrop-blur-3xl border border-white/10 p-2 pl-3 md:pl-6 rounded-[20px] md:rounded-[24px] focus-within:border-emerald-500/30 focus-within:bg-white/[0.04] transition-all duration-500 focus-within:ring-2 focus-within:ring-emerald-500/10 shadow-[0_0_50px_rgba(0,0,0,0.3)] min-w-0">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.txt,.md"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
            title="Upload Context Document"
            className={`p-2 rounded-xl transition-all ${
              loading ? 'opacity-50 cursor-not-allowed text-zinc-600' : 'text-zinc-500 hover:text-emerald-400 hover:bg-white/5'
            }`}
          >
            <Paperclip size={18} />
          </button>

          <div className="relative border-r border-white/10 pr-4 mr-2 shrink-0" ref={dropdownRef}>
            <button 
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-1.5 md:gap-2 text-[10px] font-bold uppercase tracking-[0.1em] text-zinc-500 hover:text-zinc-300 transition-colors whitespace-nowrap"
            >
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${currentModel.iconColor}`} /> 
              <span className="hidden sm:inline truncate max-w-[90px] md:max-w-none">{currentModel.label}</span>
              {isDropdownOpen ? <ChevronDown size={12} className="ml-0.5 opacity-50 shrink-0" /> : <ChevronUp size={12} className="ml-0.5 opacity-50 shrink-0" />}
            </button>

            <AnimatePresence>
              {isDropdownOpen && (
                <motion.div 
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute bottom-full left-0 mb-4 w-[240px] bg-[#0c0c0c] border border-white/10 rounded-xl overflow-hidden shadow-[0_0_30px_rgba(0,0,0,0.8)] z-50 py-2"
                >
                  <div className="px-4 py-2 text-[10px] text-zinc-500 font-medium normal-case tracking-normal">Model</div>
                  {models.map(model => (
                    <button
                      key={model.id}
                      onClick={() => {
                        setLlmProvider(model.id as 'gemini' | 'sambanova' | 'groq' | 'cerebras' | 'mistral');
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 flex items-center justify-between hover:bg-white/5 transition-colors ${llmProvider === model.id ? 'bg-white/[0.03]' : ''}`}
                    >
                      <span className={`text-[12px] normal-case tracking-normal font-medium ${llmProvider === model.id ? 'text-zinc-200' : 'text-zinc-400'}`}>
                        {model.label}
                      </span>
                      {llmProvider === model.id && (
                        <div className={`w-1.5 h-1.5 rounded-full ${model.iconColor} shadow-[0_0_10px_currentColor]`} />
                      )}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <input
            className="flex-1 min-w-0 bg-transparent border-none py-4 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none font-medium selection:bg-emerald-500/30"
            placeholder="Initialize research sequence..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !loading && handleAnalyze()}
          />
          <button
            onClick={() => handleAnalyze()}
            disabled={loading || !topic}
            className={`shrink-0 px-3 md:px-6 py-3 rounded-[16px] md:rounded-[18px] transition-all flex items-center justify-center font-bold tracking-tighter uppercase text-xs border border-white/5 ${
              loading || !topic 
                ? 'bg-black/20 text-zinc-700 cursor-not-allowed' 
                : 'bg-zinc-900 text-zinc-300 hover:text-emerald-400 hover:bg-black hover:border-emerald-500/30 hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
            ) : (
              <>
                <span className="hidden md:flex items-center gap-2">Execute <Send size={14} /></span>
                <span className="flex md:hidden"><Send size={16} /></span>
              </>
            )}
          </button>
        </div>
        
        <div className="hidden sm:flex mt-4 justify-center gap-4 md:gap-8 text-[9px] uppercase tracking-[0.25em] text-zinc-600 font-bold opacity-60 items-center">
          <span className="flex items-center gap-2 hover:text-cyan-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-cyan-500" /> Multi-Agent_Orchestration</span>
          <span className="flex items-center gap-2 hover:text-amber-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-amber-500" /> RAG_Pipeline_Active</span>
          <span className="flex items-center gap-2 hover:text-purple-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-purple-500" /> Latency: <span id="latency-metric">~300ms</span></span>
        </div>
      </div>
    </div>
  );
}
