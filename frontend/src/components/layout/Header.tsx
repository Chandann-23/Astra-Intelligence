import React from 'react';
import { Menu, ChevronRight, ChevronLeft, BookOpen, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';

interface HeaderProps {
  isMobileNavOpen: boolean;
  setIsMobileNavOpen: (v: boolean) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (v: boolean) => void;
  isHistoryOpen: boolean;
  setIsHistoryOpen: (v: boolean) => void;
  ragMode: "general" | "strict_local";
  setRagMode: (mode: "general" | "strict_local") => void;
}

export default function Header({
  isMobileNavOpen,
  setIsMobileNavOpen,
  isSidebarOpen,
  setIsSidebarOpen,
  isHistoryOpen,
  setIsHistoryOpen,
  ragMode,
  setRagMode
}: HeaderProps) {
  const router = useRouter();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };
  return (
    <header className="p-4 md:p-6 border-b border-white/5 flex justify-between items-center bg-zinc-950/40 backdrop-blur-2xl relative z-30 shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
      {/* Left Sidebar Toggle (History) */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsMobileNavOpen(true)}
          className="p-2 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl text-zinc-400 hover:text-white hover:bg-white/10 transition-all md:hidden"
        >
          <Menu size={18} />
        </button>
        <div className="hidden md:flex items-center">
          <button
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
            className="p-2 bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl text-zinc-400 hover:text-white hover:bg-white/10 transition-all group"
            title="Toggle Chat History"
          >
            {isHistoryOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </div>
      </div>

      {/* Astra Header - Centered using flex */}
      <div className="flex-1 flex justify-center items-center text-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 to-zinc-500 tracking-tight">
            Astra Engine
          </h1>
          <p className="text-[10px] text-zinc-500 uppercase tracking-[0.3em] mt-1 font-bold">Multi-Agent Intelligence</p>
        </div>
      </div>

      {/* Right Controls (RAG Mode & Engine Insights Toggle) */}
      <div className="flex items-center justify-end gap-3">
        <button 
          onClick={() => setRagMode(ragMode === "general" ? "strict_local" : "general")}
          className={`text-[10px] uppercase tracking-widest font-bold flex items-center gap-2 px-4 py-2 rounded-xl transition-all border ${
            ragMode === "strict_local" 
              ? "bg-purple-500/20 text-purple-400 border-purple-500/50 shadow-[0_0_20px_rgba(168,85,247,0.3)] hover:scale-105" 
              : "bg-black/40 text-zinc-500 border-white/10 hover:text-zinc-300 hover:bg-white/10 hover:scale-105"
          }`}
        >
          <BookOpen size={14} />
          <span className="hidden md:inline">
            {ragMode === "strict_local" ? "Notebook Mode: On" : "Notebook Mode: Off"}
          </span>
        </button>

        <div className="hidden lg:flex items-center gap-2">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className={`p-2 backdrop-blur-xl border rounded-xl transition-all group ${
              isSidebarOpen ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400' : 'bg-white/5 border-white/10 text-zinc-400 hover:text-white hover:bg-white/10'
            }`}
            title="Toggle Engine Insights"
          >
            {isSidebarOpen ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
          </button>
          
          <button
            onClick={handleSignOut}
            className="p-2 backdrop-blur-xl border border-white/10 rounded-xl text-zinc-400 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/20 transition-all group"
            title="Sign Out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
