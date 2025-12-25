"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  role: "user" | "assistant";
  content: string | any;
}

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  onUploadFile?: (file: File) => Promise<void>;
  loading: boolean;
}

// Helper to extract text from message content
function getMessageText(content: any): string {
  if (typeof content === "string") {
    return content;
  }
  if (content && typeof content === "object") {
    if (content.text) return content.text;
    if (Array.isArray(content)) {
      return content.map(item => item.text || "").join("");
    }
  }
  return String(content);
}

export function ChatPanel({ messages, onSendMessage, onUploadFile, loading }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    setSending(true);
    const message = input;
    setInput("");
    
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      await onSendMessage(message);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
  };

  if (loading) {
    return (
      <div style={{ 
        flex: 1, 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "center",
        color: "var(--foreground-subtle)"
      }}>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-4)" }}
        >
          <div className="spinner" />
          <span>Loading conversation...</span>
        </motion.div>
      </div>
    );
  }

  return (
    <>
      {/* Messages */}
      <div className="chat-messages-container">
        {messages.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="chat-empty-state"
          >
            <div className="chat-empty-icon">
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <p className="chat-empty-text">Start the conversation</p>
            <p style={{ fontSize: "var(--text-sm)", color: "var(--foreground-subtle)", maxWidth: "240px", textAlign: "center" }}>
              Ask questions about your documents or explore new topics
            </p>
          </motion.div>
        ) : (
          <>
            <AnimatePresence mode="popLayout">
              {messages.map((message, i) => (
                <motion.div
                  key={i}
                  layout
                  initial={{ opacity: 0, y: 16, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -16 }}
                  transition={{ 
                    duration: 0.3, 
                    delay: i === messages.length - 1 ? 0 : 0,
                    ease: [0.22, 1, 0.36, 1]
                  }}
                  style={{
                    display: "flex",
                    justifyContent: message.role === "user" ? "flex-end" : "flex-start",
                    marginBottom: "var(--space-4)"
                  }}
                >
                  {/* Avatar for assistant */}
                  {message.role === "assistant" && (
                    <div style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "var(--radius-lg)",
                      background: "var(--primary-subtle)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginRight: "var(--space-3)",
                      flexShrink: 0
                    }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5z" />
                        <path d="M2 17l10 5 10-5" />
                        <path d="M2 12l10 5 10-5" />
                      </svg>
                    </div>
                  )}
                  
                  {/* Message Bubble */}
                  <div className={`chat-bubble ${message.role === "user" ? "chat-bubble-user" : "chat-bubble-assistant"}`}>
                    {getMessageText(message.content)}
                  </div>

                  {/* Avatar for user */}
                  {message.role === "user" && (
                    <div style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "var(--radius-lg)",
                      background: "var(--primary)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginLeft: "var(--space-3)",
                      flexShrink: 0,
                      color: "var(--primary-foreground)"
                    }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            
            {/* Typing indicator */}
            <AnimatePresence>
              {sending && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  style={{ display: "flex", alignItems: "flex-start", marginBottom: "var(--space-4)" }}
                >
                  <div style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "var(--radius-lg)",
                    background: "var(--primary-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginRight: "var(--space-3)",
                    flexShrink: 0
                  }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <div className="typing-indicator">
                    <div style={{ display: "flex", gap: "6px" }}>
                      <div className="dot" />
                      <div className="dot" />
                      <div className="dot" />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="chat-input-area"
      >
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end" }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="chat-textarea"
            rows={1}
            disabled={sending}
            style={{ flex: 1 }}
          />
          
          {/* Attachment Button */}
          {onUploadFile && (
            <>
              <input
                type="file"
                onChange={async (e) => {
                  const files = e.target.files;
                  if (files) {
                    for (let i = 0; i < files.length; i++) {
                      await onUploadFile(files[i]);
                    }
                    e.target.value = "";
                  }
                }}
                multiple
                style={{ display: "none" }}
                id="file-upload-chat"
              />
              <motion.button
                type="button"
                onClick={() => document.getElementById("file-upload-chat")?.click()}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="btn-chat-action"
                title="Attach files"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </motion.button>
            </>
          )}
          
          {/* Send Button */}
          <motion.button
            type="submit"
            disabled={!input.trim() || sending}
            whileHover={{ scale: input.trim() && !sending ? 1.05 : 1 }}
            whileTap={{ scale: input.trim() && !sending ? 0.95 : 1 }}
            className={`btn-send ${input.trim() && !sending ? 'active' : ''}`}
          >
            {sending ? (
              <motion.svg
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
              >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </motion.svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
            )}
          </motion.button>
        </form>
      </motion.div>
    </>
  );
}