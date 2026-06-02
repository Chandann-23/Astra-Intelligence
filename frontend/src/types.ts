export interface Message {
  id: string;
  role: 'user' | 'astra';
  content: string;
  type?: 'text' | 'analysis';
  retrievedNodes?: string[];
  isMemoryAccessed?: boolean;
}
