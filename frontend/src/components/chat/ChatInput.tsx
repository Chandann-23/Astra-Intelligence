import React from 'react';
import { Paperclip, Send } from 'lucide-react';

interface ChatInputProps {
  loading: boolean;
  topic: string;
  setTopic: (v: string) => void;
  handleAnalyze: () => void;
  fileInputRef: React.RefObject<HTMLInputElement>;
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
  return (
    <div className="p-4 md:p-8 bg-gradient-to-t from-black via-black/80 to-transparent relative z-20 shrink-0">
      <div className="max-w-4xl mx-auto relative group">
        <div className="absolute inset-0 bg-emerald-500/5 blur-2xl rounded-[32px] opacity-0 group-focus-within:opacity-100 transition-opacity duration-700 pointer-events-none" />
        
        <div className="relative flex items-center gap-4 bg-white/[0.02] backdrop-blur-3xl border border-white/10 p-2 pl-6 rounded-[24px] focus-within:border-emerald-500/30 focus-within:bg-white/[0.04] transition-all duration-500 focus-within:ring-2 focus-within:ring-emerald-500/10 shadow-[0_0_50px_rgba(0,0,0,0.3)]">
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
          
          <input
            className="flex-1 bg-transparent border-none py-4 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none font-medium selection:bg-emerald-500/30"
            placeholder="Initialize research sequence..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !loading && handleAnalyze()}
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !topic}
            className={`px-6 py-3 rounded-[18px] transition-all flex items-center justify-center font-bold tracking-tighter uppercase text-xs border border-white/5 ${
              loading || !topic 
                ? 'bg-black/20 text-zinc-700 cursor-not-allowed' 
                : 'bg-zinc-900 text-zinc-300 hover:text-emerald-400 hover:bg-black hover:border-emerald-500/30 hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
            ) : (
              <span className="flex items-center gap-2">Execute <Send size={14} /></span>
            )}
          </button>
        </div>
        
        <div className="mt-4 flex justify-center gap-8 text-[9px] uppercase tracking-[0.25em] text-zinc-600 font-bold opacity-60">
          <span className="flex items-center gap-2 hover:text-emerald-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-emerald-500" /> GLM-5.1_Model</span>
          <span className="flex items-center gap-2 hover:text-cyan-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-cyan-500" /> Multi-Agent_Orchestration</span>
          <span className="flex items-center gap-2 hover:text-amber-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-amber-500" /> RAG_Pipeline_Active</span>
          <span className="flex items-center gap-2 hover:text-purple-400 transition-colors cursor-default"><div className="w-1 h-1 rounded-full bg-purple-500" /> Latency: <span id="latency-metric">~300ms</span></span>
        </div>
      </div>
    </div>
  );
}
