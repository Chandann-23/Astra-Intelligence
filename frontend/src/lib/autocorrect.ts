export const AUTOCORRECT_MAP: { [key: string]: string } = {
  // Travel / General English
  'itinery': 'itinerary',
  'itineries': 'itineraries',
  'itinerery': 'itinerary',
  'recieve': 'receive',
  'recieved': 'received',
  'recieveing': 'receiving',
  'seperate': 'separate',
  'seperated': 'separated',
  'seperately': 'separately',
  'occured': 'occurred',
  'occuring': 'occurring',
  'definetly': 'definitely',
  'definately': 'definitely',
  'goverment': 'government',
  'enviroment': 'environment',
  'commited': 'committed',
  'untill': 'until',
  'becuase': 'because',
  'accomodate': 'accommodate',
  'accommdate': 'accommodate',
  'embarass': 'embarrass',
  'resturant': 'restaurant',
  'suprise': 'surprise',
  'suprised': 'surprised',
  'tommorrow': 'tomorrow',
  'freind': 'friend',
  'freinds': 'friends',
  'alot': 'a lot',
  'whent': 'went',
  'abour': 'about',

  // Tech / Proper Nouns
  'chandan': 'Chandan',
  'bengaluru': 'Bengaluru',
  'bangalore': 'Bangalore',
  'iyenger': 'Iyengar',
  'iyengar': 'Iyengar',
  'astra': 'Astra',
  'gemini': 'Gemini',
  'mistral': 'Mistral',
  'langgraph': 'LangGraph',
  'langchain': 'LangChain',
  'crewai': 'CrewAI',
  'autogen': 'AutoGen',
  'llm': 'LLM',
  'llms': 'LLMs',
  'rag': 'RAG',
  'neo4j': 'Neo4j',
  'postgres': 'PostgreSQL',
  'postgresql': 'PostgreSQL',
  'supabase': 'Supabase',
  'fastapi': 'FastAPI',
  'nextjs': 'Next.js',
  'reactjs': 'React',
  'javascript': 'JavaScript',
  'typescript': 'TypeScript',
  'python': 'Python',
};

/**
 * Applies autocorrect to a full string, replacing misspelled words while preserving casing and punctuation.
 */
export const applyAutocorrect = (text: string): string => {
  if (!text) return text;
  
  // Split by whitespace boundaries while retaining the whitespaces in the resulting array
  return text.split(/(\s+)/).map(part => {
    // Skip if this part is just whitespace
    if (/^\s+$/.test(part)) return part;
    
    // Extract punctuation to look up the clean word
    const cleanWord = part.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?]/g, "").toLowerCase();
    const mapped = AUTOCORRECT_MAP[cleanWord];
    
    if (mapped) {
      // Replace only the matched word part, keeping punctuation intact
      return part.replace(new RegExp(cleanWord, 'i'), mapped);
    }
    return part;
  }).join('');
};
