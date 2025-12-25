"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface FileInfo {
  name: string;
  size: number;
  extension: string;
}

interface FileNavigatorProps {
  files: FileInfo[];
  selectedFile: string | null;
  onSelectFile: (filename: string) => void;
  onUploadFile: (file: File) => void;
  onDeleteFile: (filename: string) => void;
  onRenameFile: (oldName: string, newName: string) => void;
}

const FILE_ICONS: Record<string, { icon: string; color: string }> = {
  ".pdf": { icon: "📕", color: "#ef4444" },
  ".md": { icon: "📝", color: "#3b82f6" },
  ".txt": { icon: "📄", color: "#64748b" },
  ".html": { icon: "🌐", color: "#f97316" },
  ".csv": { icon: "📊", color: "#22c55e" },
  ".xlsx": { icon: "📗", color: "#22c55e" },
  ".xls": { icon: "📗", color: "#22c55e" },
  ".png": { icon: "🖼️", color: "#a855f7" },
  ".jpg": { icon: "🖼️", color: "#a855f7" },
  ".jpeg": { icon: "🖼️", color: "#a855f7" },
  ".gif": { icon: "🖼️", color: "#a855f7" },
  ".webp": { icon: "🖼️", color: "#a855f7" },
};

export function FileNavigator({
  files,
  selectedFile,
  onSelectFile,
  onUploadFile,
  onDeleteFile,
  onRenameFile,
}: FileNavigatorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; file: string } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        onUploadFile(files[i]);
      }
      e.target.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        onUploadFile(files[i]);
      }
    }
  };

  const handleContextMenu = (e: React.MouseEvent, filename: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, file: filename });
  };

  const handleRename = () => {
    if (contextMenu) {
      setEditingFile(contextMenu.file);
      setEditName(contextMenu.file);
      setContextMenu(null);
    }
  };

  const handleDeleteClick = () => {
    if (contextMenu) {
      setDeleteConfirm(contextMenu.file);
      setContextMenu(null);
    }
  };

  const confirmDelete = () => {
    if (deleteConfirm) {
      onDeleteFile(deleteConfirm);
      setDeleteConfirm(null);
    }
  };

  const submitRename = () => {
    if (editingFile && editName && editName !== editingFile) {
      onRenameFile(editingFile, editName);
    }
    setEditingFile(null);
    setEditName("");
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getIcon = (ext: string) => FILE_ICONS[ext.toLowerCase()]?.icon || "📄";

  return (
    <div 
      style={{ 
        height: "100%", 
        display: "flex", 
        flexDirection: "column", 
        padding: "var(--space-4)",
        paddingTop: "var(--space-3)"
      }}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Upload button */}
      <motion.button
        onClick={handleUploadClick}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "var(--space-2)",
          padding: "var(--space-3) var(--space-4)",
          marginBottom: "var(--space-4)",
          borderRadius: "var(--radius-xl)",
          background: dragOver ? "var(--primary-subtle)" : "var(--background)",
          border: `2px dashed ${dragOver ? "var(--primary)" : "var(--border)"}`,
          cursor: "pointer",
          color: dragOver ? "var(--primary)" : "var(--foreground-muted)",
          fontSize: "var(--text-sm)",
          fontWeight: 500,
          transition: "all var(--duration-fast) var(--ease-out)"
        }}
        onMouseEnter={(e) => {
          if (!dragOver) {
            e.currentTarget.style.background = "var(--accent-subtle)";
            e.currentTarget.style.borderColor = "var(--primary)";
            e.currentTarget.style.color = "var(--primary)";
          }
        }}
        onMouseLeave={(e) => {
          if (!dragOver) {
            e.currentTarget.style.background = "var(--background)";
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.color = "var(--foreground-muted)";
          }
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
        </svg>
        {dragOver ? "Drop files here" : "Upload Files"}
      </motion.button>
      
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileChange}
        style={{ display: "none" }}
        multiple
        accept=".pdf,.md,.txt,.html,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp"
      />

      {/* File list */}
      <div style={{ flex: 1, overflow: "auto", marginTop: "var(--space-1)" }}>
        <AnimatePresence mode="popLayout">
          {files.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ 
                textAlign: "center", 
                padding: "var(--space-8) var(--space-4)", 
                color: "var(--foreground-subtle)",
                fontSize: "var(--text-sm)"
              }}
            >
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto var(--space-3)", opacity: 0.3 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <p>No files yet</p>
              <p style={{ fontSize: "var(--text-xs)", marginTop: "var(--space-1)", opacity: 0.7 }}>
                Upload or drag files here
              </p>
            </motion.div>
          ) : (
            files.map((file, index) => (
              <motion.div
                key={file.name}
                layout
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16, height: 0 }}
                transition={{ delay: index * 0.03, duration: 0.2 }}
                className={`file-item ${selectedFile === file.name ? "active" : ""}`}
                onClick={() => onSelectFile(file.name)}
                onContextMenu={(e) => handleContextMenu(e, file.name)}
              >
                <span className="file-icon">{getIcon(file.extension)}</span>
                {editingFile === file.name ? (
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={submitRename}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") submitRename();
                      if (e.key === "Escape") {
                        setEditingFile(null);
                        setEditName("");
                      }
                    }}
                    className="input"
                    style={{ 
                      padding: "var(--space-1) var(--space-2)", 
                      fontSize: "var(--text-sm)", 
                      flex: 1,
                      height: "28px"
                    }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <span className="file-name">{file.name}</span>
                    <span style={{ 
                      fontSize: "var(--text-xs)", 
                      color: "var(--foreground-subtle)", 
                      flexShrink: 0,
                      fontFamily: "var(--font-mono)"
                    }}>
                      {formatSize(file.size)}
                    </span>
                  </>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Context Menu */}
      <AnimatePresence>
        {contextMenu && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{ position: "fixed", inset: 0, zIndex: 99 }}
              onClick={() => setContextMenu(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -4 }}
              transition={{ duration: 0.15 }}
              className="context-menu"
              style={{
                position: "fixed",
                left: contextMenu.x,
                top: contextMenu.y,
                zIndex: 100,
              }}
            >
              <button onClick={handleRename} className="context-menu-item">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                </svg>
                Rename
              </button>
              <button onClick={handleDeleteClick} className="context-menu-item context-menu-item--danger">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                Delete
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="modal-backdrop"
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 8 }}
              transition={{ type: "spring", damping: 25, stiffness: 350 }}
              onClick={(e) => e.stopPropagation()}
              className="modal-content"
            >
              <h3 className="modal-title">Delete File?</h3>
              <p className="modal-description">
                Are you sure you want to delete <strong style={{ color: "var(--foreground)" }}>{deleteConfirm}</strong>? 
                This action cannot be undone.
              </p>
              <div className="modal-actions">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setDeleteConfirm(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={confirmDelete}
                  className="btn btn-danger"
                >
                  Delete
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}