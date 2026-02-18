import { memo } from "react";
import { Handle, Position } from "@xyflow/react";

type BaseNodeData = {
  text: string;
  backendId: number;
  onDelete: (backendId: number) => void;
};

function TriggerNode({ data }: { data: BaseNodeData }) {
  return (
    <div
      style={{
        padding: "16px",
        border: "2px solid #7c4dff",
        borderRadius: "8px",
        background: "white",
        minWidth: "220px",
        boxShadow: "0 4px 6px rgba(124, 77, 255, 0.2)",
      }}
    >
      <div style={{ marginBottom: "12px" }}>
        <div
          style={{
            fontSize: "11px",
            fontWeight: "600",
            color: "#6b7280",
            marginBottom: "4px",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          🚀 Trigger (Entry Point)
        </div>
        <div
          style={{
            fontSize: "14px",
            fontWeight: "500",
            color: "#1f2937",
            wordBreak: "break-word",
          }}
        >
          {data.text}
        </div>
      </div>

      <button
        onClick={() => data.onDelete(data.backendId)}
        style={{
          width: "100%",
          padding: "6px",
          fontSize: "12px",
          color: "#dc2626",
          border: "1px solid #fca5a5",
          borderRadius: "4px",
          background: "#fef2f2",
          cursor: "pointer",
          fontWeight: "500",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#fee2e2";
          e.currentTarget.style.borderColor = "#f87171";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "#fef2f2";
          e.currentTarget.style.borderColor = "#fca5a5";
        }}
      >
        Delete Node
      </button>

      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

function ResponseNode({ data }: { data: BaseNodeData }) {
  return (
    <div
      style={{
        padding: "16px",
        border: "2px solid #16a34a",
        borderRadius: "8px",
        background: "white",
        minWidth: "220px",
        boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
      }}
    >
      {/* Input connection point at top */}
      <Handle type="target" position={Position.Top} />

      <div style={{ marginBottom: "12px" }}>
        <div
          style={{
            fontSize: "11px",
            fontWeight: "600",
            color: "#6b7280",
            marginBottom: "4px",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          💬 Response
        </div>
        <div
          style={{
            fontSize: "14px",
            fontWeight: "500",
            color: "#1f2937",
            wordBreak: "break-word",
          }}
        >
          {data.text}
        </div>
      </div>

      <button
        onClick={() => data.onDelete(data.backendId)}
        style={{
          width: "100%",
          padding: "6px",
          fontSize: "12px",
          color: "#dc2626",
          border: "1px solid #fca5a5",
          borderRadius: "4px",
          background: "#fef2f2",
          cursor: "pointer",
          fontWeight: "500",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#fee2e2";
          e.currentTarget.style.borderColor = "#f87171";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "#fef2f2";
          e.currentTarget.style.borderColor = "#fca5a5";
        }}
      >
        Delete Node
      </button>

      {/* Output connection point at bottom */}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export const MemoTriggerNode = memo(TriggerNode);
export const MemoResponseNode = memo(ResponseNode);
