import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

export type Message = {
  id: string;
  role: 'user' | 'astra';
  content: string;
  type?: 'text' | 'analysis';
  retrievedNodes?: string[];
  isMemoryAccessed?: boolean;
};

interface ChatState {
  // Session State
  userId: string | null;
  setUserId: (id: string | null) => void;
  
  // Current Chat State
  currentChatId: string;
  messages: Message[];
  topic: string;
  logs: string[];
  
  // Execution State
  loading: boolean;
  isWarmingUp: boolean;
  activeAgent: string | null;
  ragMode: 'general' | 'strict_local';
  llmProvider: 'gemini' | 'sambanova' | 'groq' | 'cerebras';
  
  // Layout State
  isSidebarOpen: boolean;
  isHistoryOpen: boolean;
  isMobileNavOpen: boolean;
  isGraphVisible: boolean;
  expandedPanel: 'logs' | 'strategy' | 'graph' | null;
  
  // Actions
  setTopic: (topic: string) => void;
  setLoading: (loading: boolean) => void;
  setIsWarmingUp: (warmingUp: boolean) => void;
  setActiveAgent: (agent: string | null) => void;
  setRagMode: (mode: 'general' | 'strict_local') => void;
  setLlmProvider: (provider: 'gemini' | 'sambanova' | 'groq' | 'cerebras') => void;
  addMessage: (message: Message) => void;
  setMessages: (updater: Message[] | ((prev: Message[]) => Message[])) => void;
  updateLastAstraMessage: (content: string, retrievedNodes?: string[], isMemoryAccessed?: boolean) => void;
  addLog: (log: string) => void;
  setLogs: (updater: string[] | ((prev: string[]) => string[])) => void;
  
  // Layout Actions
  setIsSidebarOpen: (isOpen: boolean) => void;
  setIsHistoryOpen: (isOpen: boolean) => void;
  setIsMobileNavOpen: (isOpen: boolean) => void;
  setIsGraphVisible: (isVisible: boolean) => void;
  setExpandedPanel: (panel: 'logs' | 'strategy' | 'graph' | null) => void;
  
  // Core Functions
  resetChat: () => void;
  loadChat: (chatId: string, loadedMessages: Message[]) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  userId: null,
  setUserId: (id) => set({ userId: id }),
  
  currentChatId: uuidv4(),
  messages: [{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }],
  topic: '',
  logs: [],
  
  loading: false,
  isWarmingUp: false,
  activeAgent: null,
  ragMode: 'general',
  llmProvider: 'gemini',
  
  isSidebarOpen: true,
  isHistoryOpen: true,
  isMobileNavOpen: false,
  isGraphVisible: false,
  expandedPanel: null,
  
  setTopic: (topic) => set({ topic }),
  setLoading: (loading) => set({ loading }),
  setIsWarmingUp: (isWarmingUp) => set({ isWarmingUp }),
  setActiveAgent: (activeAgent) => set({ activeAgent }),
  setRagMode: (ragMode) => set({ ragMode }),
  setLlmProvider: (llmProvider) => set({ llmProvider }),
  
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (updater) => set((state) => ({ 
    messages: typeof updater === 'function' ? updater(state.messages) : updater 
  })),
  
  updateLastAstraMessage: (content, retrievedNodes, isMemoryAccessed) => set((state) => {
    const newMessages = [...state.messages];
    const lastMessage = newMessages[newMessages.length - 1];
    
    if (lastMessage && lastMessage.role === 'astra') {
      lastMessage.content = content;
      if (retrievedNodes !== undefined) lastMessage.retrievedNodes = retrievedNodes;
      if (isMemoryAccessed !== undefined) lastMessage.isMemoryAccessed = isMemoryAccessed;
    } else {
      newMessages.push({
        id: Date.now().toString(),
        role: 'astra',
        content,
        type: 'analysis',
        retrievedNodes,
        isMemoryAccessed
      });
    }
    return { messages: newMessages };
  }),
  
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  setLogs: (updater) => set((state) => ({ 
    logs: typeof updater === 'function' ? updater(state.logs) : updater 
  })),
  
  setIsSidebarOpen: (isSidebarOpen) => set({ isSidebarOpen }),
  setIsHistoryOpen: (isHistoryOpen) => set({ isHistoryOpen }),
  setIsMobileNavOpen: (isMobileNavOpen) => set({ isMobileNavOpen }),
  setIsGraphVisible: (isGraphVisible) => set({ isGraphVisible }),
  setExpandedPanel: (expandedPanel) => set({ expandedPanel }),
  
  resetChat: () => set({
    currentChatId: uuidv4(),
    messages: [{ id: '1', role: 'astra', content: "System initialized. How can I assist with your research today?" }],
    topic: '',
    logs: [],
    loading: false,
    isWarmingUp: false,
    activeAgent: null,
  }),
  
  loadChat: (chatId, loadedMessages) => set({
    currentChatId: chatId,
    messages: loadedMessages,
    topic: '',
    logs: [],
    loading: false,
    isWarmingUp: false,
    activeAgent: null,
    isMobileNavOpen: false
  })
}));
