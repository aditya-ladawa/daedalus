"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface FileViewerProps {
  chatId: string;
  filename: string | null;
  onClose?: () => void;
}

export function FileViewer({ chatId, filename, onClose }: FileViewerProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!filename) {
      setContent(null);
      setBlobUrl(null);
      return;
    }

    loadFile();

    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [chatId, filename]);

  const loadFile = async () => {
    if (!filename) return;

    setLoading(true);
    setError(null);
    setContent(null);
    setBlobUrl(null);

    const ext = filename.split(".").pop()?.toLowerCase() || "";
    const fileUrl = `/conversations/${chatId}/files/${encodeURIComponent(filename)}`;

    try {
      const res = await fetch(fileUrl);
      
      if (!res.ok) {
        throw new Error("Failed to load file");
      }

      if (["png", "jpg", "jpeg", "gif", "webp"].includes(ext)) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
      } else if (ext === "pdf") {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
      } else if (["md", "txt", "html", "csv"].includes(ext)) {
        const text = await res.text();
        setContent(text);
      } else if (["xlsx", "xls"].includes(ext)) {
        setContent("EXCEL_FILE");
      } else {
        setContent("UNSUPPORTED");
      }
    } catch (err) {
      setError("Failed to load file");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getExtension = () => filename?.split(".").pop()?.toLowerCase() || "";

  if (!filename) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ 
          height: "100%", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center",
          flexDirection: "column",
          gap: "var(--space-4)",
          color: "var(--foreground-subtle)"
        }}
      >
        <div style={{
          width: "80px",
          height: "80px",
          borderRadius: "var(--radius-2xl)",
          background: "var(--background-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ opacity: 0.4 }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <p style={{ fontSize: "var(--text-base)", fontWeight: 500 }}>Select a file to view</p>
        <p style={{ fontSize: "var(--text-sm)", opacity: 0.7 }}>Choose a file from the sidebar</p>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "var(--space-4)" }}>
        <div className="spinner" />
        <p style={{ color: "var(--foreground-muted)", fontSize: "var(--text-sm)" }}>Loading file...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "var(--space-4)" }}>
        <div style={{
          width: "64px",
          height: "64px",
          borderRadius: "var(--radius-xl)",
          background: "var(--error-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--error)" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
        </div>
        <p style={{ color: "var(--error)", fontWeight: 500 }}>{error}</p>
        <button onClick={loadFile} className="btn btn-secondary">
          Try Again
        </button>
      </div>
    );
  }

  const ext = getExtension();

  // Image viewer
  if (["png", "jpg", "jpeg", "gif", "webp"].includes(ext) && blobUrl) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        style={{ 
          height: "100%", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center", 
          padding: "var(--space-4)",
          background: "var(--background-subtle)",
          borderRadius: "var(--radius-xl)"
        }}
      >
        <img
          src={blobUrl}
          alt={filename}
          style={{ 
            maxWidth: "100%", 
            maxHeight: "100%", 
            objectFit: "contain", 
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--elevation-3)"
          }}
        />
      </motion.div>
    );
  }

  // PDF viewer
  if (ext === "pdf" && blobUrl) {
    return (
      <motion.iframe
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        src={blobUrl}
        style={{ 
          width: "100%", 
          height: "100%", 
          border: "none", 
          borderRadius: "var(--radius-xl)",
          background: "white"
        }}
        title={filename}
      />
    );
  }

  // HTML viewer
  if (ext === "html" && content) {
    return (
      <motion.iframe
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        srcDoc={content}
        style={{ 
          width: "100%", 
          height: "100%", 
          border: "1px solid var(--border)", 
          borderRadius: "var(--radius-xl)", 
          background: "white" 
        }}
        title={filename}
        sandbox="allow-scripts"
      />
    );
  }

  // CSV viewer
  if (ext === "csv" && content) {
    const rows = content.split("\n").filter(row => row.trim());
    const headers = rows[0]?.split(",").map(h => h.trim()) || [];
    const data = rows.slice(1).map(row => row.split(",").map(cell => cell.trim()));

    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ 
          height: "100%", 
          overflow: "auto",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          background: "var(--background-elevated)"
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}>
          <thead>
            <tr>
              {headers.map((header, i) => (
                <th
                  key={i}
                  style={{
                    padding: "var(--space-3) var(--space-4)",
                    textAlign: "left",
                    borderBottom: "2px solid var(--border)",
                    background: "var(--background-subtle)",
                    position: "sticky",
                    top: 0,
                    fontWeight: 600,
                    fontSize: "var(--text-xs)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "var(--foreground-muted)"
                  }}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr 
                key={i}
                style={{ 
                  transition: "background var(--duration-fast) var(--ease-out)"
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--accent-subtle)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                {row.map((cell, j) => (
                  <td
                    key={j}
                    style={{
                      padding: "var(--space-3) var(--space-4)",
                      borderBottom: "1px solid var(--border-muted)",
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </motion.div>
    );
  }

  // Markdown viewer
  if (ext === "md" && content) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ 
          height: "100%", 
          overflow: "auto",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          background: "var(--background-elevated)",
          padding: "var(--space-6)"
        }}
      >
        <div style={{ maxWidth: "720px", margin: "0 auto" }}>
          <MarkdownRenderer content={content} />
        </div>
      </motion.div>
    );
  }

  // Text viewer
  if (ext === "txt" && content) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ 
          height: "100%", 
          overflow: "auto",
          borderRadius: "var(--radius-xl)",
          border: "1px solid var(--border)",
          background: "var(--background-elevated)",
          padding: "var(--space-5)"
        }}
      >
        <pre style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-sm)",
          lineHeight: "var(--leading-relaxed)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          color: "var(--foreground)",
          margin: 0
        }}>
          {content}
        </pre>
      </motion.div>
    );
  }

  // Excel file
  if (content === "EXCEL_FILE") {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "var(--space-4)" }}>
        <div style={{
          width: "80px",
          height: "80px",
          borderRadius: "var(--radius-2xl)",
          background: "var(--success-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}>
          <span style={{ fontSize: "2.5rem" }}>📗</span>
        </div>
        <p style={{ color: "var(--foreground)", fontWeight: 500 }}>Excel files cannot be previewed</p>
        <a
          href={`/conversations/${chatId}/files/${encodeURIComponent(filename)}`}
          download={filename}
          className="btn btn-primary"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          Download {filename}
        </a>
      </div>
    );
  }

  // Unsupported
  return (
    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={{
        width: "80px",
        height: "80px",
        borderRadius: "var(--radius-2xl)",
        background: "var(--warning-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" strokeWidth="1.5">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <path d="M12 11v6M12 17h.01" />
        </svg>
      </div>
      <p style={{ color: "var(--foreground)", fontWeight: 500 }}>Preview not available</p>
      <p style={{ color: "var(--foreground-muted)", fontSize: "var(--text-sm)" }}>This file type is not supported for preview</p>
      <a
        href={`/conversations/${chatId}/files/${encodeURIComponent(filename)}`}
        download={filename}
        className="btn btn-secondary"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
        </svg>
        Download File
      </a>
    </div>
  );
}

// Simple markdown renderer
function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  
  return (
    <div style={{ 
      fontFamily: "var(--font-body)", 
      lineHeight: "var(--leading-relaxed)",
      color: "var(--foreground)"
    }}>
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith("### ")) {
          return (
            <h3 key={i} style={{ 
              fontSize: "var(--text-lg)", 
              fontWeight: 600, 
              marginTop: "var(--space-6)", 
              marginBottom: "var(--space-3)",
              color: "var(--foreground)"
            }}>
              {line.slice(4)}
            </h3>
          );
        }
        if (line.startsWith("## ")) {
          return (
            <h2 key={i} style={{ 
              fontSize: "var(--text-xl)", 
              fontWeight: 600, 
              marginTop: "var(--space-8)", 
              marginBottom: "var(--space-4)",
              color: "var(--foreground)"
            }}>
              {line.slice(3)}
            </h2>
          );
        }
        if (line.startsWith("# ")) {
          return (
            <h1 key={i} style={{ 
              fontSize: "var(--text-2xl)", 
              fontWeight: 700, 
              marginTop: "var(--space-8)", 
              marginBottom: "var(--space-4)",
              color: "var(--foreground)"
            }}>
              {line.slice(2)}
            </h1>
          );
        }
        // Code blocks
        if (line.startsWith("```")) {
          return null;
        }
        // Empty lines
        if (!line.trim()) {
          return <div key={i} style={{ height: "var(--space-4)" }} />;
        }
        // Regular paragraphs
        return (
          <p key={i} style={{ 
            marginBottom: "var(--space-3)",
            color: "var(--foreground-muted)"
          }}>
            {line}
          </p>
        );
      })}
    </div>
  );
}