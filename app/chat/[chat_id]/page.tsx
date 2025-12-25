"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ThemeToggle } from "../../components/ThemeToggle";
import { FileNavigator } from "../../components/FileNavigator";
import { FileViewer } from "../../components/FileViewer";
import { ChatPanel } from "../../components/ChatPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface FileInfo {
  name: string;
  size: number;
  extension: string;
}

// Collapse button component
const CollapseButton = ({ 
  direction, 
  onClick, 
  title 
}: { 
  direction: "left" | "right"; 
  onClick: () => void; 
  title: string;
}) => (
  <motion.button
    onClick={onClick}
    whileHover={{ scale: 1.05 }}
    whileTap={{ scale: 0.95 }}
    style={{
      width: "32px",
      height: "32px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: "var(--radius-lg)",
      background: "var(--background)",
      border: "1px solid var(--border)",
      cursor: "pointer",
      color: "var(--foreground-muted)",
      transition: "all var(--duration-fast) var(--ease-out)",
      flexShrink: 0
    }}
    title={title}
    onMouseEnter={(e) => {
      e.currentTarget.style.background = "var(--accent-subtle)";
      e.currentTarget.style.borderColor = "var(--primary)";
      e.currentTarget.style.color = "var(--primary)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.background = "var(--background)";
      e.currentTarget.style.borderColor = "var(--border)";
      e.currentTarget.style.color = "var(--foreground-muted)";
    }}
  >
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={direction === "left" ? "M15 18l-6-6 6-6" : "M9 18l6-6-6-6"} />
    </svg>
  </motion.button>
);

export default function ChatPage() {
  const params = useParams();
  const chatId = params.chat_id as string;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [title, setTitle] = useState("Untitled Project");
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Panel widths
  const [leftWidth, setLeftWidth] = useState(280);
  const [rightWidth, setRightWidth] = useState(420);
  
  // Saved widths for restore
  const [savedLeftWidth, setSavedLeftWidth] = useState(280);
  const [savedRightWidth, setSavedRightWidth] = useState(420);
  
  // Collapse states
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  
  // Resize states
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);

  // Constraints
  const MIN_WIDTH = 240;
  const MAX_LEFT_WIDTH = 400;
  const COLLAPSED_WIDTH = 52;

  useEffect(() => {
    loadConversation();
    loadFiles();
  }, [chatId]);

  const loadConversation = async () => {
    try {
      const res = await fetch(`/conversations/${chatId}`);
      const data = await res.json();
      if (data.messages) setMessages(data.messages);
      if (data.title) setTitle(data.title);
    } catch (error) {
      console.error("Failed to load conversation:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadFiles = async () => {
    try {
      const res = await fetch(`/conversations/${chatId}/files`);
      const data = await res.json();
      setFiles(data.files || []);
    } catch (error) {
      console.error("Failed to load files:", error);
    }
  };

  const sendMessage = async (content: string) => {
    const userMessage: Message = { role: "user", content };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const res = await fetch(`/conversations/${chatId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content }),
      });
      const data = await res.json();
      if (data.response) {
        setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
      }
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      await fetch(`/conversations/${chatId}/files`, { method: "POST", body: formData });
      loadFiles();
    } catch (error) {
      console.error("Failed to upload file:", error);
    }
  };

  const deleteFile = async (filename: string) => {
    try {
      await fetch(`/conversations/${chatId}/files/${encodeURIComponent(filename)}`, { method: "DELETE" });
      if (selectedFile === filename) setSelectedFile(null);
      loadFiles();
    } catch (error) {
      console.error("Failed to delete file:", error);
    }
  };

  const renameFile = async (oldName: string, newName: string) => {
    try {
      await fetch(`/conversations/${chatId}/files/${encodeURIComponent(oldName)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_name: newName }),
      });
      if (selectedFile === oldName) setSelectedFile(newName);
      loadFiles();
    } catch (error) {
      console.error("Failed to rename file:", error);
    }
  };

  // Toggle collapse
  const toggleLeftPanel = useCallback(() => {
    if (leftCollapsed) {
      setLeftWidth(savedLeftWidth);
      setLeftCollapsed(false);
    } else {
      setSavedLeftWidth(leftWidth);
      setLeftWidth(COLLAPSED_WIDTH);
      setLeftCollapsed(true);
    }
  }, [leftCollapsed, leftWidth, savedLeftWidth]);

  const toggleRightPanel = useCallback(() => {
    if (rightCollapsed) {
      setRightWidth(savedRightWidth);
      setRightCollapsed(false);
    } else {
      setSavedRightWidth(rightWidth);
      setRightWidth(COLLAPSED_WIDTH);
      setRightCollapsed(true);
    }
  }, [rightCollapsed, rightWidth, savedRightWidth]);

  // Resize handlers
  const handleLeftResize = useCallback((e: MouseEvent) => {
    const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_LEFT_WIDTH, e.clientX));
    setLeftWidth(newWidth);
    if (leftCollapsed) setLeftCollapsed(false);
  }, [leftCollapsed]);

  const handleRightResize = useCallback((e: MouseEvent) => {
    const newWidth = Math.max(MIN_WIDTH, Math.min(window.innerWidth * 0.45, window.innerWidth - e.clientX));
    setRightWidth(newWidth);
    if (rightCollapsed) setRightCollapsed(false);
  }, [rightCollapsed]);

  const handleMouseUp = useCallback(() => {
    setIsResizingLeft(false);
    setIsResizingRight(false);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingLeft) handleLeftResize(e);
      if (isResizingRight) handleRightResize(e);
    };

    if (isResizingLeft || isResizingRight) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingLeft, isResizingRight, handleLeftResize, handleRightResize, handleMouseUp]);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--background)", position: "relative" }}>
      {/* Resize Overlay - Prevents iframes from capturing mouse events during resize */}
      {(isResizingLeft || isResizingRight) && (
        <div 
          style={{ 
            position: "fixed", 
            inset: 0, 
            zIndex: 9999, 
            cursor: "col-resize",
            background: "transparent"
          }} 
        />
      )}
      
      {/* Header */}
      <motion.header 
        initial={{ y: -60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        style={{
          height: "60px",
          borderBottom: "1px solid var(--border)",
          padding: "0 var(--space-5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--background-elevated)",
          flexShrink: 0
        }}
      >
        <Link 
          href="/" 
          style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "var(--space-3)",
            padding: "var(--space-2)",
            marginLeft: "calc(-1 * var(--space-2))",
            borderRadius: "var(--radius-lg)",
            transition: "all var(--duration-fast) var(--ease-out)",
            textDecoration: "none",
            color: "var(--foreground)"
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-subtle)"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
        >
          <motion.svg 
            width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            whileHover={{ x: -2 }}
            transition={{ type: "spring", stiffness: 400 }}
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </motion.svg>
          <span className="logo">DAEDALUS</span>
        </Link>
        <ThemeToggle />
      </motion.header>

      {/* Main Content */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left Panel - Files */}
        <motion.div
          animate={{ width: leftWidth }}
          transition={{ type: "spring", stiffness: 400, damping: 35 }}
          style={{
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            background: "var(--background-elevated)",
            borderRight: "1px solid var(--border)"
          }}
        >
          <AnimatePresence mode="wait">
            {leftCollapsed ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "var(--space-4)" }}
              >
                <CollapseButton direction="right" onClick={toggleLeftPanel} title="Expand files" />
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{ height: "100%", display: "flex", flexDirection: "column" }}
              >
                <div className="panel-header">
                  <span className="panel-title">Files</span>
                  <CollapseButton direction="left" onClick={toggleLeftPanel} title="Collapse" />
                </div>
                <div style={{ flex: 1, overflow: "hidden" }}>
                  <FileNavigator
                    files={files}
                    selectedFile={selectedFile}
                    onSelectFile={setSelectedFile}
                    onUploadFile={uploadFile}
                    onDeleteFile={deleteFile}
                    onRenameFile={renameFile}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Left Resize Handle */}
        <div
          onMouseDown={(e) => { e.preventDefault(); setIsResizingLeft(true); }}
          className={`resize-handle ${isResizingLeft ? 'active' : ''}`}
        />

        {/* Center Panel - File Viewer */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden", background: "var(--background)" }}>
          <div className="panel-header">
            <motion.span 
              key={selectedFile || "none"}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="panel-title"
              style={{ color: selectedFile ? "var(--foreground)" : "var(--foreground-subtle)" }}
            >
              {selectedFile || "No file selected"}
            </motion.span>
            {selectedFile && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setSelectedFile(null)}
                style={{
                  width: "32px",
                  height: "32px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "var(--radius-lg)",
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  cursor: "pointer",
                  color: "var(--foreground-muted)",
                  transition: "all var(--duration-fast) var(--ease-out)"
                }}
                title="Close file"
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "var(--error-subtle)";
                  e.currentTarget.style.borderColor = "var(--error)";
                  e.currentTarget.style.color = "var(--error)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "var(--background)";
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.color = "var(--foreground-muted)";
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </motion.button>
            )}
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "var(--space-4)" }}>
            <FileViewer chatId={chatId} filename={selectedFile} onClose={() => setSelectedFile(null)} />
          </div>
        </div>

        {/* Right Resize Handle */}
        <div
          onMouseDown={(e) => { e.preventDefault(); setIsResizingRight(true); }}
          className={`resize-handle ${isResizingRight ? 'active' : ''}`}
        />

        {/* Right Panel - Chat */}
        <motion.div
          animate={{ width: rightWidth }}
          transition={{ type: "spring", stiffness: 400, damping: 35 }}
          style={{
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            background: "var(--background-elevated)",
            borderLeft: "1px solid var(--border)"
          }}
        >
          <AnimatePresence mode="wait">
            {rightCollapsed ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", paddingTop: "var(--space-4)" }}
              >
                <CollapseButton direction="left" onClick={toggleRightPanel} title="Expand chat" />
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{ height: "100%", display: "flex", flexDirection: "column" }}
              >
                <div className="panel-header">
                  <CollapseButton direction="right" onClick={toggleRightPanel} title="Collapse" />
                  <motion.span 
                    key={title}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="panel-title"
                    style={{ textAlign: "center" }}
                  >
                    {title}
                  </motion.span>
                  <div style={{ width: "32px" }} />
                </div>
                <ChatPanel
                  messages={messages}
                  onSendMessage={sendMessage}
                  onUploadFile={uploadFile}
                  loading={loading}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}