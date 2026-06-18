import React, { useEffect, useState } from 'react';
import { Plus, MessageSquare, Info, RefreshCw, User, LogOut, X, Trash2, Check } from 'lucide-react';
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
  const [userName, setUserName] = useState<string | null>(null);
  const [userAvatar, setUserAvatar] = useState<string | null>(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const router = useRouter();

  const initiateDelete = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    setDeletingId(chatId);
  };

  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingId(null);
  };

  const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    try {
      // Step 1: Delete messages first to prevent foreign key constraints
      const { error: messagesError } = await supabase
        .from('messages')
        .delete()
        .eq('chat_id', chatId);
        
      if (messagesError) throw messagesError;

      // Step 2: Delete the chat itself
      const { error: chatError } = await supabase
        .from('chats')
        .delete()
        .eq('id', chatId);

      if (chatError) throw chatError;

      // Step 3: If this was the active chat, reset workspace
      if (chatId === currentChatId) {
        resetChat();
      }

      showToast("Chat deleted successfully");
      fetchChats();
    } catch (err) {
      console.error("Failed to delete chat:", err);
      showToast("Failed to delete chat");
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const email = data.user?.email || null;
      setUserEmail(email);
      setUserName(data.user?.user_metadata?.full_name || email?.split('@')[0] || 'User');
      setUserAvatar(data.user?.user_metadata?.avatar_url || data.user?.user_metadata?.picture || null);
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
    // Refresh periodically AND whenever the active chatId changes
    const interval = setInterval(fetchChats, 5000);
    return () => clearInterval(interval);
  }, [currentChatId]);

  return (
    <div className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 md:relative md:translate-x-0 w-[240px] h-full bg-zinc-950 border-r border-white/5 flex flex-col py-4 space-y-4 ${isMobileNavOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
      {/* Header Area */}
      <div className="px-4 flex items-center justify-between">
        <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">History</span>
        <div className="flex items-center gap-2">
          <button onClick={fetchChats} className={`p-1 text-zinc-500 hover:text-white transition-all ${loading ? 'animate-spin' : ''}`}>
            <RefreshCw size={14} />
          </button>
          {/* Close button — only visible on mobile */}
          <button
            onClick={() => setIsMobileNavOpen(false)}
            className="md:hidden p-1 text-zinc-500 hover:text-white transition-all"
          >
            <X size={16} />
          </button>
        </div>
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
        {chats.map(chat => {
          const isDeleting = deletingId === chat.id;
          const isActive = currentChatId === chat.id;
          
          return (
            <div 
              key={chat.id}
              className={`w-full rounded-xl flex items-center justify-between transition-all border group/item relative ${
                isActive ? 'bg-cyan-500/10 border-cyan-500/20' : 'bg-transparent border-transparent hover:bg-white/5'
              }`}
            >
              <button 
                onClick={() => {
                  loadChat(chat.id);
                  setIsMobileNavOpen(false); // Auto-close on mobile after selecting chat
                }}
                className="flex-1 min-w-0 pl-3 pr-10 py-3 flex items-center gap-3 cursor-pointer text-left"
              >
                <MessageSquare size={14} className={`${isActive ? 'text-cyan-400' : 'text-zinc-600 group-hover/item:text-zinc-400'} shrink-0 transition-colors`} />
                <span className={`text-xs truncate ${isActive ? 'text-cyan-50 font-medium' : 'text-zinc-400 group-hover/item:text-zinc-300'} transition-colors ${isDeleting ? 'pr-14' : 'pr-6'}`}>
                  {chat.title}
                </span>
              </button>
              
              <div className="absolute right-2 flex items-center gap-1 z-10">
                {isDeleting ? (
                  <>
                    <button
                      onClick={(e) => handleDeleteChat(e, chat.id)}
                      className="p-1 hover:bg-emerald-500/20 rounded text-emerald-400 transition-colors cursor-pointer"
                      title="Confirm delete"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={cancelDelete}
                      className="p-1 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                      title="Cancel"
                    >
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={(e) => initiateDelete(e, chat.id)}
                    className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-rose-400 opacity-0 group-hover/item:opacity-100 transition-opacity duration-200 cursor-pointer"
                    title="Delete Chat"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Area: ChatGPT Style User Profile Dropdown */}
      <div className="px-2 mt-auto pt-4 pb-2 relative">
        {isProfileMenuOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsProfileMenuOpen(false)}
            />
            <div className="absolute bottom-full left-2 w-[calc(100%-16px)] mb-2 bg-[#2f2f2f] border border-white/5 rounded-xl shadow-[0_4px_24px_rgba(0,0,0,0.5)] p-1.5 flex flex-col z-50">
              <button 
                onClick={() => {
                  setIsAboutOpen(true);
                  setIsProfileMenuOpen(false);
                }}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/10 text-[14px] text-zinc-200 transition-colors w-full text-left"
              >
                <Info size={16} /> About Astra
              </button>
              <div className="h-px bg-white/10 my-1 mx-2"></div>
              <button 
                onClick={handleSignOut}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/10 text-[14px] text-zinc-200 transition-colors w-full text-left"
              >
                <LogOut size={16} /> Log out
              </button>
            </div>
          </>
        )}

        <button 
          onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
          className={`flex items-center justify-between w-full h-[52px] rounded-xl px-2 transition-all ${isProfileMenuOpen ? 'bg-white/10' : 'bg-transparent hover:bg-white/5'}`}
        >
          <div className="flex items-center gap-2 overflow-hidden">
            {userAvatar ? (
              <img src={userAvatar} alt="Profile" className="w-8 h-8 rounded-full object-cover shrink-0" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 font-semibold text-sm">
                {userName?.charAt(0).toUpperCase() || 'U'}
              </div>
            )}
            <div className="flex flex-col items-start truncate">
              <span className="text-[14px] font-medium text-zinc-200 truncate w-36 text-left">{userName || 'Loading...'}</span>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}
