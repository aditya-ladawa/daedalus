"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ThemeToggle } from "../components/ThemeToggle";

export default function NewChatPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || loading) return;

    setLoading(true);
    
    try {
      const res = await fetch("/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initial_message: message }),
      });
      
      const data = await res.json();
      
      if (data.id) {
        router.push(`/chat/${data.id}`);
      }
    } catch (error) {
      console.error("Failed to create conversation:", error);
      setLoading(false);
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--background)" }}>
      <div className="theme-toggle">
        <ThemeToggle />
      </div>

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
      </motion.header>

      {/* Main content */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "var(--space-6)" }}>
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ maxWidth: "640px", width: "100%", textAlign: "center" }}
        >
          <h1 style={{ fontSize: "var(--text-4xl)", fontWeight: 700, marginBottom: "var(--space-2)", color: "var(--foreground)" }}>
            Start a new project
          </h1>
          <p style={{ color: "var(--foreground-muted)", fontSize: "var(--text-lg)", marginBottom: "var(--space-10)" }}>
            Begin your research journey with a question or topic
          </p>

          <form onSubmit={handleSubmit}>
            <div style={{ position: "relative" }}>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What would you like to explore?"
                className="input"
                style={{
                  minHeight: "160px",
                  resize: "none",
                  padding: "var(--space-5)",
                  paddingBottom: "var(--space-16)",
                  fontSize: "var(--text-lg)",
                  lineHeight: "var(--leading-relaxed)"
                }}
                disabled={loading}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                autoFocus
              />
              <div style={{
                position: "absolute",
                bottom: "var(--space-4)",
                right: "var(--space-4)",
                display: "flex",
                gap: "var(--space-3)"
              }}>
                <button
                  type="submit"
                  disabled={!message.trim() || loading}
                  className={`btn btn-primary ${message.trim() && !loading ? 'active' : ''}`}
                  style={{ padding: "var(--space-3) var(--space-6)" }}
                >
                  {loading ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <div className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }} />
                      <span>Creating...</span>
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                      </svg>
                      <span>Start Project</span>
                    </div>
                  )}
                </button>
              </div>
            </div>
          </form>
        </motion.div>
      </main>
    </div>
  );
}