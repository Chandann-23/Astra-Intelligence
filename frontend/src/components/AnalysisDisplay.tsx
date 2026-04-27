"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";

interface AnalysisDisplayProps {
  result: string;
}

const AnalysisDisplay: React.FC<AnalysisDisplayProps> = ({ result }) => {
  const cleanText = (text: string) => {
    return text
      .replace(/^(\s*#+)([a-zA-Z0-9])/gm, '$1 $2') // Robust regex to insert space: #Introduction -> # Introduction
      .replace(/\|{2,}/g, '|')
      .replace(/_{2,}/g, '_')
      .trim();
  };

  const cleanedResult = cleanText(result);
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    setDisplayedText("");
    setIsTyping(true);
    let i = 0;
    const intervalId = setInterval(() => {
      setDisplayedText((prev) => prev + cleanedResult.charAt(i));
      i++;
      if (i >= cleanedResult.length) {
        clearInterval(intervalId);
        setIsTyping(false);
      }
    }, 10); // Slightly faster for markdown

    return () => clearInterval(intervalId);
  }, [cleanedResult]);

  return (
    <div className="w-full max-w-4xl mx-auto bg-black/40 backdrop-blur-xl border border-emerald-500/20 rounded-2xl overflow-hidden shadow-2xl relative transition-all duration-500">
      {/* Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.05)_50%),linear-gradient(90deg,rgba(16,185,129,0.01),rgba(16,185,129,0.01),rgba(16,185,129,0.01))] bg-[length:100%_4px,3px_100%] z-20 opacity-30" />
      
      {/* Terminal Header */}
      <div 
        className="border-b border-cyan-500/30 px-6 py-4 flex items-center justify-between relative z-30 bg-[#0a0a0a]"
      >
        <div className="flex space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/40" />
        </div>
        <div className="text-[10px] uppercase tracking-[0.3em] font-bold text-zinc-500">
          Analysis_Stream
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            <motion.div
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="w-1.5 h-1.5 rounded-full bg-emerald-500"
            />
            <span className="text-[9px] font-bold text-emerald-500 uppercase tracking-tighter">
              Live
            </span>
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="p-8 min-h-[200px] relative overflow-hidden z-30">
        <div className="relative z-0 max-w-none">
          <div 
            className="text-white font-sans text-left"
            style={{ 
              fontFamily: "'Inter', sans-serif",
              lineHeight: '1.7',
              whiteSpace: 'pre-line'
            }}
          >
            <ReactMarkdown
              components={{
                h1: ({node, children, ...props}) => (
                  <h1 className="text-[1.5rem] font-[600] text-cyan-400 mt-10 mb-8 tracking-tight" {...props}>
                    {String(children).replace(/#+/g, '').trim()}
                  </h1>
                ),
                h2: ({node, children, ...props}) => (
                  <h2 className="text-[1.5rem] font-[600] text-cyan-400 mt-8 mb-6 tracking-tight" {...props}>
                    {String(children).replace(/#+/g, '').trim()}
                  </h2>
                ),
                h3: ({node, children, ...props}) => (
                  <h3 className="text-xl font-[600] text-cyan-400 mt-6 mb-4 tracking-tight" {...props}>
                    {String(children).replace(/#+/g, '').trim()}
                  </h3>
                ),
                p: ({node, ...props}) => <p className="text-white mb-5 leading-[1.7] opacity-100 font-[400]" {...props} />,
                strong: ({node, ...props}) => <strong className="text-cyan-400 font-[700]" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-3 mb-5 text-white opacity-100 font-[400]" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-3 mb-5 text-white opacity-100 font-[400]" {...props} />,
                li: ({node, ...props}) => <li className="marker:text-cyan-500 font-[400] mb-2" {...props} />,
                code: ({node, ...props}) => <code className="bg-zinc-800 text-white px-2 py-1 rounded font-mono text-[0.9em] border border-white/10" {...props} />,
              }}
            >
              {displayedText}
            </ReactMarkdown>
            {isTyping && (
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                className="inline-block w-1.5 h-4 ml-1 bg-emerald-500 align-middle"
              />
            )}
          </div>
        </div>
      </div>

      {/* Terminal Footer */}
      <div className="bg-emerald-950/10 border-t border-emerald-500/10 px-6 py-2 flex justify-between items-center text-[9px] opacity-40 uppercase tracking-widest relative z-30 font-mono">
        <div>Ln {displayedText.split('\n').length}, Col {displayedText.split('\n').pop()?.length || 0}</div>
        <div>UTF-8</div>
        <div className="flex items-center gap-1.5">
          <div className="w-1 h-1 rounded-full bg-emerald-500" />
          Llama-3.3-Groq
        </div>
      </div>
    </div>
  );
};

export default AnalysisDisplay;
