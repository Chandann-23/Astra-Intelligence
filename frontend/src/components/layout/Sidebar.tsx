import React from 'react';
import { Plus, MessageSquare, Info } from 'lucide-react';
import { Message } from '@/types';

interface SidebarProps {
  isMobileNavOpen: boolean;
  setIsMobileNavOpen: (v: boolean) => void;
  resetChat: () => void;
  showToast: (msg: string) => void;
  isAboutOpen: boolean;
  setIsAboutOpen: (v: boolean) => void;
}

export default function Sidebar({
  isMobileNavOpen,
  setIsMobileNavOpen,
  resetChat,
  showToast,
  isAboutOpen,
  setIsAboutOpen
}: SidebarProps) {
  return (
    <div className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 md:relative md:translate-x-0 w-16 bg-zinc-950 border-r border-white/5 flex flex-col items-center py-4 space-y-4 ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      {/* New Chat Button */}
      <button 
        onClick={resetChat}
        className="w-10 h-10 rounded-2xl bg-zinc-900 border border-white/5 flex items-center justify-center hover:bg-white/10 hover:border-white/20 transition-all group shadow-xl"
        title="New Chat"
      >
        <Plus size={16} className="text-zinc-300 group-hover:text-white group-hover:scale-110 transition-transform" />
      </button>

      {/* Recent History Section */}
      <div className="flex-1 flex flex-col items-center space-y-3 py-4">
        <button 
          onClick={() => showToast("Previous Research Sessions: Coming Soon")}
          className="w-10 h-10 rounded-2xl bg-transparent border border-transparent flex items-center justify-center hover:bg-white/5 transition-all cursor-pointer group" 
          title="Previous Research Sessions"
        >
          <MessageSquare size={14} className="text-zinc-600 group-hover:text-zinc-300 transition-colors" />
        </button>
        <button 
          onClick={() => showToast("Previous Research Sessions: Coming Soon")}
          className="w-10 h-10 rounded-2xl bg-transparent border border-transparent flex items-center justify-center hover:bg-white/5 transition-all cursor-pointer group" 
          title="Previous Research Sessions"
        >
          <MessageSquare size={14} className="text-zinc-600 group-hover:text-zinc-300 transition-colors" />
        </button>
      </div>

      {/* About Astra Button */}
      <button 
        onClick={() => setIsAboutOpen(!isAboutOpen)}
        className="w-10 h-10 rounded-2xl bg-transparent border border-transparent flex items-center justify-center hover:bg-white/5 transition-all group"
        title="About Astra"
      >
        <Info size={16} className="text-zinc-600 group-hover:text-zinc-300 transition-colors" />
      </button>
    </div>
  );
}
