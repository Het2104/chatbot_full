"use client";

import { memo, CSSProperties, MouseEvent } from "react";
import { Handle, Position } from "@xyflow/react";

// ─── Types ────────────────────────────────────────────────────────────────────

export type NodeData = {
  text: string;          // Trigger label or button name
  bot_message: string;   // Bot response shown to the user
  paths: string[];       // Labels of directly connected child nodes
  backendId: number;
  onDelete: (backendId: number) => void;
};

// ─── Shared helpers ───────────────────────────────────────────────────────────

const stopPropagation = (e: MouseEvent) => e.stopPropagation();

const deleteBtn: CSSProperties = {
  background: "transparent",
  border: "none",
  cursor: "pointer",
  padding: "2px 5px",
  borderRadius: "4px",
  color: "#ef4444",
  fontSize: "13px",
  lineHeight: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

// ─── Shared node shell ────────────────────────────────────────────────────────

function NodeShell({
  accentColor,
  badge,
  badgeBg,
  badgeText,
  data,
  children,
}: {
  accentColor: string;
  badge: string;
  badgeBg: string;
  badgeText: string;
  data: NodeData;
  children?: React.ReactNode;
}) {
  return (
    <div
      style={{
        minWidth: 220,
        maxWidth: 260,
        background: "#ffffff",
        border: `1.5px solid ${accentColor}`,
        borderRadius: 10,
        boxShadow: "0 2px 12px rgba(99,102,241,0.08), 0 1px 3px rgba(0,0,0,0.06)",
        overflow: "hidden",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "7px 10px",
          background: "#f8fafc",
          borderBottom: `1px solid ${accentColor}22`,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: 1,
            textTransform: "uppercase",
            color: badgeText,
            background: badgeBg,
            padding: "2px 8px",
            borderRadius: 20,
            border: `1px solid ${accentColor}44`,
          }}
        >
          {badge}
        </span>

        <button
          style={deleteBtn}
          title="Delete node"
          onClick={(e) => {
            stopPropagation(e);
            data.onDelete(data.backendId);
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#fef2f2")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div style={{ padding: "10px 12px 12px" }}>
        <Field
          label={badge === "TRIGGER" ? "Trigger Label" : "Button Name"}
          value={data.text}
          valueColor="#1e293b"
          fieldBg="#eef2ff"
        />

        <Field
          label="Bot Message"
          value={data.bot_message || "—"}
          valueColor={data.bot_message ? "#166534" : "#94a3b8"}
          fieldBg={data.bot_message ? "#f0fdf4" : "#f8fafc"}
          style={{ marginTop: 8 }}
        />

        {children}
      </div>
    </div>
  );
}

// ─── Field ────────────────────────────────────────────────────────────────────

function Field({
  label,
  value,
  valueColor,
  fieldBg,
  style,
}: {
  label: string;
  value: string;
  valueColor: string;
  fieldBg: string;
  style?: CSSProperties;
}) {
  return (
    <div style={style}>
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: 0.8,
          textTransform: "uppercase",
          color: "#94a3b8",
          marginBottom: 3,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 12,
          color: valueColor,
          lineHeight: 1.45,
          wordBreak: "break-word",
          background: fieldBg,
          borderRadius: 6,
          padding: "5px 8px",
          minHeight: 24,
          border: "1px solid #e2e8f0",
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ─── Paths section ────────────────────────────────────────────────────────────

function PathsSection({
  paths,
  accentColor,
  pillBg,
  pillText,
}: {
  paths: string[];
  accentColor: string;
  pillBg: string;
  pillText: string;
}) {
  return (
    <div style={{ marginTop: 10 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 5,
        }}
      >
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: 0.8,
            textTransform: "uppercase",
            color: "#94a3b8",
          }}
        >
          Paths
        </span>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: accentColor,
            background: pillBg,
            borderRadius: "50%",
            width: 18,
            height: 18,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: `1px solid ${accentColor}44`,
          }}
        >
          {paths.length}
        </span>
      </div>

      {paths.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {paths.map((p, i) => (
            <span
              key={i}
              style={{
                fontSize: 10,
                color: pillText,
                background: pillBg,
                border: `1px solid ${accentColor}44`,
                borderRadius: 20,
                padding: "2px 8px",
                maxWidth: 100,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={p}
            >
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── TriggerNode ─────────────────────────────────────────────────────────────

function TriggerNode({ data }: { data: NodeData }) {
  return (
    <NodeShell
      accentColor="#6366f1"
      badge="TRIGGER"
      badgeBg="#eef2ff"
      badgeText="#4338ca"
      data={data}
    >
      <PathsSection
        paths={data.paths}
        accentColor="#6366f1"
        pillBg="#eef2ff"
        pillText="#4338ca"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#6366f1", border: "2px solid #fff", width: 10, height: 10 }}
      />
    </NodeShell>
  );
}

// ─── ResponseNode (ACTION) ───────────────────────────────────────────────────

function ResponseNode({ data }: { data: NodeData }) {
  return (
    <NodeShell
      accentColor="#e2e8f0"
      badge="ACTION"
      badgeBg="#f8fafc"
      badgeText="#475569"
      data={data}
    >
      <PathsSection
        paths={data.paths}
        accentColor="#6366f1"
        pillBg="#eef2ff"
        pillText="#4338ca"
      />
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#6366f1", border: "2px solid #fff", width: 10, height: 10 }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#6366f1", border: "2px solid #fff", width: 10, height: 10 }}
      />
    </NodeShell>
  );
}

// ─── Exports ──────────────────────────────────────────────────────────────────

export const MemoTriggerNode = memo(TriggerNode);
export const MemoResponseNode = memo(ResponseNode);
