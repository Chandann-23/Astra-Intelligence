import React, { useEffect, useState } from 'react';
import { Plus, MessageSquare, Info, RefreshCw, User, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';

interface SidebarProps {
  isMobileNavOpen: boolean;
  setIsMobileNavOpen: (v: boolean) => void;
  resetChat: () => void;
  showToast: (msg: string) => void;
  isAboutOpen: boolean;
  setIsAboutOpen: (v: boolean) => void;
  loadChat: (chatId: string) => void;
  currentChatId: string;
}

export default function Sidebar({
  isMobileNavOpen,
  setIsMobileNavOpen,
  resetChat,
  showToast,
  isAboutOpen,
  setIsAboutOpen,
  loadChat,
  currentChatId
}: SidebarProps) {
  const [chats, setChats] = useState<{ id: string, title: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setUserEmail(data.user?.email || null);
    });
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const fetchChats = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('chats')
        .select('id, title, updated_at')
        .order('updated_at', { ascending: false });
        
      if (error) throw error;
      if (data) setChats(data);
    } catch (e) {
      console.error("Failed to fetch chats", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChats();
    // Refresh periodically
    const interval = setInterval(fetchChats, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 md:relative md:translate-x-0 w-[240px] bg-zinc-950 border-r border-white/5 flex flex-col py-4 space-y-4 ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      {/* Header Area */}
      <div className="px-4 flex items-center justify-between">
        <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">History</span>
        <button onClick={fetchChats} className={`p-1 text-zinc-500 hover:text-white transition-all ${loading ? 'animate-spin' : ''}`}>
          <RefreshCw size={14} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-4">
        <button 
          onClick={resetChat}
          className="w-full h-10 rounded-xl bg-zinc-900 border border-white/5 flex items-center justify-center gap-2 hover:bg-white/10 hover:border-white/20 transition-all group shadow-xl"
          title="New Chat"
        >
          <Plus size={16} className="text-zinc-300 group-hover:text-white transition-colors" />
          <span className="text-sm font-medium text-zinc-300 group-hover:text-white transition-colors">New Research</span>
        </button>
      </div>

      {/* Recent History Section */}
      <div className="flex-1 flex flex-col px-2 space-y-1 overflow-y-auto custom-scrollbar">
        {chats.map(chat => (
          <button 
            key={chat.id}
            onClick={() => loadChat(chat.id)}
            className={`w-full px-3 py-3 rounded-xl flex items-center gap-3 transition-all cursor-pointer group text-left ${
              currentChatId === chat.id ? 'bg-cyan-500/10 border-cyan-500/20' : 'bg-transparent border-transparent hover:bg-white/5'
            } border`} 
          >
            <MessageSquare size={14} className={`${currentChatId === chat.id ? 'text-cyan-400' : 'text-zinc-600 group-hover:text-zinc-400'} shrink-0 transition-colors`} />
            <span className={`text-xs truncate ${currentChatId === chat.id ? 'text-cyan-50 font-medium' : 'text-zinc-400 group-hover:text-zinc-300'} transition-colors`}>
              {chat.title}
            </span>
          </button>
        ))}
      </div>

      {/* Bottom Area: About & User Profile */}
      <div className="px-4 mt-auto pt-4 border-t border-white/5 flex flex-col gap-2">
        <button 
          onClick={() => setIsAboutOpen(!isAboutOpen)}
          className="w-full h-10 rounded-xl bg-transparent border border-transparent flex items-center justify-start gap-3 hover:bg-white/5 transition-all group px-2"
        >
          <Info size={16} className="text-zinc-500 group-hover:text-zinc-300 transition-colors" />
          <span className="text-sm font-medium text-zinc-500 group-hover:text-zinc-300 transition-colors">About Astra</span>
        </button>

        <div className="flex items-center justify-between w-full h-12 rounded-xl bg-zinc-900 border border-white/5 px-3 group hover:bg-white/10 transition-all cursor-default shadow-lg">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center shrink-0">
              <User size={14} className="text-cyan-400" />
            </div>
            <span className="text-xs font-medium text-zinc-300 truncate" title={userEmail || ''}>
              {userEmail || 'Loading...'}
            </span>
          </div>
          <button 
            onClick={handleSignOut} 
            className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all" 
            title="Sign Out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
