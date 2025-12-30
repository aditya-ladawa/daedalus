"use client";

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useRenderToolCall, useDefaultTool } from "@copilotkit/react-core";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

// Type for render function props
interface RenderProps {
  args: Record<string, any>;
  status: "executing" | "complete" | "inProgress";
  result?: any;
  toolCallId?: string;
  name?: string;
}

interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "completed";
}

// Status styling configuration
const statusStyles = {
  pending: {
    background: "var(--accent-subtle)",
    borderLeft: "3px dashed var(--foreground-muted)",
    icon: "⏳",
    textDecoration: "none",
  },
  in_progress: {
    background: "rgba(245, 158, 11, 0.15)",
    borderLeft: "3px solid #f59e0b",
    icon: "🔄",
    textDecoration: "none",
  },
  completed: {
    background: "rgba(34, 197, 94, 0.15)",
    borderLeft: "3px solid #22c55e",
    icon: "✅",
    textDecoration: "line-through",
  },
};

// Shared card styles
const cardStyle: React.CSSProperties = {
  background: "var(--background-elevated)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-lg)",
  padding: "var(--space-4)",
  marginTop: "var(--space-3)",
  marginBottom: "var(--space-3)",
  boxShadow: "var(--elevation-1)",
};

// Pulse Animation for executing state
const PulseDot = () => (
  <motion.div
    style={{
      width: 8,
      height: 8,
      borderRadius: "50%",
      background: "var(--primary)",
      display: "inline-block",
      marginLeft: "var(--space-2)",
    }}
    animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
    transition={{ duration: 1.5, repeat: Infinity }}
  />
);

// Todo item component
const TodoItemView = ({ todo }: { todo: TodoItem }) => {
  const style = statusStyles[todo.status];
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      style={{
        padding: "var(--space-2) var(--space-3)",
        background: style.background,
        borderLeft: style.borderLeft,
        borderRadius: "var(--radius-sm)",
        marginBottom: "var(--space-1)",
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
      }}
    >
      <span>{style.icon}</span>
      <span style={{ textDecoration: style.textDecoration, flex: 1, color: "var(--foreground)" }}>
        {todo.content}
      </span>
    </motion.div>
  );
};

export function ToolCallRenderer() {
  // Collapsible state for think_strategically
  const [thinkExpanded, setThinkExpanded] = useState<Record<string, boolean>>({});

  // Web Search Tool
  useRenderToolCall({
    name: "web_search",
    render: ({ args, status, result }) => (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "var(--space-3)" }}>
          <motion.div
            animate={status === "executing" ? { rotate: 360 } : {}}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            style={{ 
              marginRight: "var(--space-3)",
              color: "var(--primary)",
              display: "flex"
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </motion.div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: "var(--foreground)", display: "flex", alignItems: "center" }}>
              Web Search
              {status === "executing" && <PulseDot />}
            </div>
          </div>
        </div>
        
        {/* Improved Query Visibility */}
        <div style={{marginBottom: "var(--space-3)" }}>
          <div style={{ 
            color: "var(--foreground-muted)", 
            fontSize: "0.85em", 
            marginBottom: "var(--space-1)",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            fontWeight: 600
          }}>
            Query
          </div>
          <div style={{ 
            background: "var(--background-subtle)", 
            padding: "var(--space-2) var(--space-3)", 
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-muted)",
            color: "var(--primary-700)",
            fontFamily: "var(--font-mono)",
            fontSize: "0.9em",
            fontWeight: 500
          }}>
            {args?.query || "Analyzing request..."}
          </div>
        </div>

        {status === "complete" && result && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
              background: "var(--background)",
              padding: "var(--space-3)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              maxHeight: "200px",
              overflow: "auto",
              fontSize: "0.9em",
              lineHeight: 1.6,
              color: "var(--foreground-muted)", // Explicit color
            }}
          >
            {result}
          </motion.div>
        )}
      </motion.div>
    ),
  });

  // Read Todos Tool
  useRenderToolCall({
    name: "read_todos",
    render: ({ status, result }) => (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "var(--space-3)" }}>
          <div style={{ marginRight: "var(--space-3)", color: "var(--primary)" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
          <div style={{ fontWeight: 600, color: "var(--foreground)" }}>
            Reading Todos
            {status === "executing" && <PulseDot />}
          </div>
        </div>
        
        {status === "complete" && result && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {typeof result === "string" ? (
              <div style={{ color: "var(--foreground-muted)", fontSize: "0.9em", fontStyle: "italic" }}>
                {result}
              </div>
            ) : (
              <div>
                {(result as TodoItem[]).map((todo, i) => (
                  <TodoItemView key={i} todo={todo} />
                ))}
              </div>
            )}
          </motion.div>
        )}
      </motion.div>
    ),
  });

  // Write Todos Tool
  useRenderToolCall({
    name: "write_todos",
    render: ({ args, status }) => {
      const todos = args?.todos as TodoItem[] | undefined;
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={cardStyle}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: "var(--space-3)" }}>
            <div style={{ marginRight: "var(--space-3)", color: "var(--primary)" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </div>
            <div style={{ fontWeight: 600, color: "var(--foreground)" }}>
              {status === "executing" ? "Updating Todos..." : "Todos Updated"}
              {status === "executing" && <PulseDot />}
            </div>
          </div>
          
          {todos && todos.length > 0 && (
            <div style={{ marginBottom: "var(--space-2)" }}>
              {todos.map((todo, i) => (
                <TodoItemView key={i} todo={todo} />
              ))}
            </div>
          )}
          
          {status === "complete" && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ 
                color: "var(--success)", 
                fontSize: "0.9em", 
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: "var(--space-2)"
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Updated successfully
            </motion.div>
          )}
        </motion.div>
      );
    },
  });

  // Think Strategically Tool
  useRenderToolCall({
    name: "think_strategically",
    render: ({ args, status }) => {
      const reflectionKey = args?.reflection?.substring(0, 50) || "default";
      const isExpanded = thinkExpanded[reflectionKey] ?? true; // Default to expanded for better visibility
      
      return (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            ...cardStyle,
            borderColor: "var(--primary-200)",
            background: "linear-gradient(to right, var(--primary-50), var(--background-elevated))"
          }}
        >
          <button
            onClick={() => setThinkExpanded((prev) => ({ ...prev, [reflectionKey]: !isExpanded }))}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
              color: "var(--foreground)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center" }}>
              <motion.div
                animate={status === "executing" ? { 
                  scale: [1, 1.2, 1],
                  filter: ["brightness(1)", "brightness(1.5)", "brightness(1)"]
                } : {}}
                transition={{ duration: 2, repeat: Infinity }}
                style={{ marginRight: "var(--space-3)", color: "var(--primary)" }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" />
                  <path d="M12 6v6l4 2" />
                </svg>
              </motion.div>
              <strong style={{ color: "var(--primary-900)" }}>
                {status === "executing" ? "Thinking Strategically..." : "Strategic Reflection"}
              </strong>
              {status === "executing" && <PulseDot />}
            </div>
            
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              style={{ color: "var(--primary-500)" }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </motion.div>
          </button>
          
          <AnimatePresence>
            {(isExpanded || status === "executing") && args?.reflection && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                style={{
                  overflow: "hidden",
                }}
              >
                <div style={{ 
                  marginTop: "var(--space-3)",
                  paddingTop: "var(--space-3)",
                  borderTop: "1px solid var(--primary-100)",
                  color: "var(--foreground-muted)", // Fixed: explicitly muted foreground for visibility
                  fontSize: "0.95em",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                  fontFamily: "var(--font-sans)",
                }}>
                  {args.reflection}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      );
    },
  });

  // Default fallback for other tools
  useDefaultTool({
    render: ({ name, args, status }) => (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={cardStyle}
      >
        <div style={{ display: "flex", alignItems: "center", marginBottom: "var(--space-3)" }}>
          <div style={{ marginRight: "var(--space-3)", color: "var(--foreground-muted)" }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
          </div>
          <strong style={{ color: "var(--foreground)" }}>{name}</strong>
          {status === "executing" && <PulseDot />}
        </div>
        {args && (
          <div style={{ fontSize: "0.85em", color: "var(--foreground-muted)" }}>
            <pre style={{ 
              background: "var(--background-subtle)", 
              padding: "var(--space-3)", 
              borderRadius: "var(--radius-sm)", 
              overflow: "auto",
              border: "1px solid var(--border-muted)"
            }}>
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>
        )}
      </motion.div>
    ),
  });

  return null;
}
