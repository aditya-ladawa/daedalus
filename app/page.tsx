"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ThemeToggle } from "./components/ThemeToggle";

interface Conversation {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
}

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [renameProject, setRenameProject] = useState<{ id: string; title: string } | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/conversations");
      const data = await res.json();
      console.log("Fetched conversations:", data.conversations);
      setConversations(data.conversations || []);
    } catch (error) {
      console.error("Failed to fetch conversations:", error);
    } finally {
      setLoading(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;

    try {
      await fetch(`/conversations/${deleteConfirm}`, { method: "DELETE" });
      setConversations(conversations.filter((c) => c.id !== deleteConfirm));
      setDeleteConfirm(null);
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  };

  const handleRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameProject || !newTitle.trim() || isRenaming) return;

    setIsRenaming(true);
    try {
      const res = await fetch(`/conversations/${renameProject.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim() }),
      });

      if (res.ok) {
        setConversations(conversations.map(c => 
          c.id === renameProject.id ? { ...c, title: newTitle.trim() } : c
        ));
        setRenameProject(null);
        setNewTitle("");
      }
    } catch (error) {
      console.error("Failed to rename project:", error);
    } finally {
      setIsRenaming(false);
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(date);
  };

  const formatRelativeTime = (timestamp: number) => {
    const now = new Date().getTime() / 1000;
    const diff = now - timestamp;

    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return formatDate(timestamp);
  };

  return (
    <div className="min-h-screen">
      <div className="theme-toggle">
        <ThemeToggle />
      </div>

      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <motion.h1 
            className="hero-title"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            DAEDALUS
          </motion.h1>
          <motion.p 
            className="hero-subtitle"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            <strong>D</strong>eep <strong>A</strong>gent for <strong>E</strong>xploratory{" "}
            <strong>D</strong>iscovery and <strong>A</strong>nalytical{" "}
            <strong>L</strong>iterature <strong>U</strong>nderstanding{" "}
            <strong>S</strong>ystem
          </motion.p>
        </div>
      </section>

      {/* Projects Section */}
      <section className="projects-section">
        <div className="container">
          <motion.div 
            className="section-header"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <h2 className="section-title">Projects</h2>
            <Link href="/chat" className="btn btn-primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5v14M5 12h14" />
              </svg>
              New Project
            </Link>
          </motion.div>

          {loading ? (
            <motion.div 
              className="loading-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="spinner" />
              <p>Loading your projects...</p>
            </motion.div>
          ) : conversations.length === 0 ? (
            <motion.div 
              className="empty-state"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
            >
              <div className="empty-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
                  <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2z" />
                </svg>
              </div>
              <p>No projects yet. Start your first discovery journey.</p>
              <Link href="/chat" className="btn btn-secondary">
                Start Project
              </Link>
            </motion.div>
          ) : (
            <motion.div 
              className="project-grid"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            >
              {conversations.map((conv) => (
                <motion.div
                  key={conv.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4 }}
                >
                  <div className="card card-interactive project-card">
                    <Link
                      href={`/chat/${conv.id}`}
                      className="project-card-link"
                    >
                      <div className="project-card-content">
                        <div className="project-card-header">
                          <h3 className="project-title">{conv.title}</h3>
                        </div>
                        <div className="project-meta">
                          <div className="meta-item">
                            <span className="meta-label">Created:</span>
                            <span className="meta-value">{formatDate(conv.created_at)}</span>
                          </div>
                          <div className="meta-item">
                            <span className="meta-label">Last active:</span>
                            <span className="meta-value">{formatRelativeTime(conv.updated_at)}</span>
                          </div>
                        </div>
                        <div className="project-card-footer">
                          <span className="project-id-badge" title={conv.id}>
                            {conv.id.slice(0, 8)}
                          </span>
                        </div>
                      </div>
                    </Link>
                    <div className="project-actions">
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setRenameProject({ id: conv.id, title: conv.title });
                          setNewTitle(conv.title);
                        }}
                        className="btn btn-ghost btn-icon rename-btn"
                        title="Rename project"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDeleteConfirm(conv.id);
                        }}
                        className="btn btn-ghost btn-icon delete-btn"
                        title="Delete project"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </section>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              className="modal-content"
              initial={{ opacity: 0, scale: 0.95, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 8 }}
              transition={{ type: "spring", damping: 25, stiffness: 350 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="modal-title">Delete Project</h2>
              <p className="modal-description">
                Are you sure you want to delete this project? This action cannot be undone.
              </p>
              <div className="modal-actions">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  className="btn btn-danger"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rename Modal */}
      <AnimatePresence>
        {renameProject && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setRenameProject(null)}
          >
            <motion.div
              className="modal-content"
              initial={{ opacity: 0, scale: 0.95, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 8 }}
              transition={{ type: "spring", damping: 25, stiffness: 350 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="modal-title">Rename Project</h2>
              <form onSubmit={handleRename}>
                <input
                  type="text"
                  className="input"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Enter new title"
                  autoFocus
                  style={{ marginBottom: "var(--space-6)", width: "100%" }}
                />
                <div className="modal-actions">
                  <button
                    type="button"
                    onClick={() => setRenameProject(null)}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!newTitle.trim() || isRenaming}
                  >
                    {isRenaming ? "Renaming..." : "Rename"}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}