"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getNodes,
  createNode,
  deleteNode,
  updateNode,
  getEdges,
  createEdge,
  deleteEdge,
} from "../../../services/api";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Node as FlowNode,
  Edge,
  Connection,
  BackgroundVariant,
  NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { MemoTriggerNode, MemoResponseNode, NodeData } from "./CustomNode";

type BackendNode = {
  id: number;
  node_type: "trigger" | "response";
  text: string;
  bot_message?: string | null;
  position_x?: number | null;
  position_y?: number | null;
};

type SelectedNodeInfo = {
  backendId: number;
  type: "trigger" | "response";
  text: string;
  bot_message: string;
};

type BackendEdge = {
  id: number;
  from_node_id: number;
  to_node_id: number;
};

const nodeTypes = {
  triggerNode: MemoTriggerNode,
  responseNode: MemoResponseNode,
};

export default function WorkflowPage() {
  const params = useParams();
  const router = useRouter();
  const workflowId = params.id as string;

  const [backendNodes, setBackendNodes] = useState<BackendNode[]>([]);
  const [backendEdges, setBackendEdges] = useState<BackendEdge[]>([]);
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Node creation form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [nodeType, setNodeType] = useState<"trigger" | "response">("trigger");
  const [nodeText, setNodeText] = useState("");
  const [nodeBotMessage, setNodeBotMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Bot response side panel
  const [selectedNode, setSelectedNode] = useState<SelectedNodeInfo | null>(null);

  const loadWorkflow = async () => {
    setLoading(true);
    setError(null);
    try {
      const [nodesData, edgesData] = await Promise.all([
        getNodes(workflowId),
        getEdges(workflowId),
      ]);
      const backendNodeList = Array.isArray(nodesData) ? nodesData : [];
      const backendEdgeList = Array.isArray(edgesData) ? edgesData : [];

      setBackendNodes(backendNodeList as BackendNode[]);
      setBackendEdges(backendEdgeList as BackendEdge[]);

      // Build a quick lookup: backendId → node for path resolution
      const nodeById = new Map<number, BackendNode>();
      (backendNodeList as BackendNode[]).forEach((n) => nodeById.set(n.id, n));

      // Compute outgoing paths (child node labels) for each node
      const pathsByNodeId = new Map<number, string[]>();
      (backendEdgeList as BackendEdge[]).forEach((edge) => {
        const childNode = nodeById.get(edge.to_node_id);
        if (childNode) {
          const existing = pathsByNodeId.get(edge.from_node_id) ?? [];
          pathsByNodeId.set(edge.from_node_id, [...existing, childNode.text]);
        }
      });

      const flowNodes: FlowNode[] = (backendNodeList as BackendNode[]).map(
        (node, index) => ({
          id: `node-${node.id}`,
          type: node.node_type === "trigger" ? "triggerNode" : "responseNode",
          position: {
            x: node.position_x ?? 100 + index * 260,
            y: node.position_y ?? 120 + (index % 3) * 200,
          },
          data: {
            text: node.text,
            bot_message: node.bot_message ?? "",
            paths: pathsByNodeId.get(node.id) ?? [],
            backendId: node.id,
            onDelete: handleDeleteNode,
          } as NodeData,
        })
      );

      const flowEdges: Edge[] = (backendEdgeList as BackendEdge[])
        .map((edge) => ({
          id: `edge-${edge.id}`,
          source: `node-${edge.from_node_id}`,
          target: `node-${edge.to_node_id}`,
        }))
        .filter(
          (edge) =>
            flowNodes.some((node) => node.id === edge.source) &&
            flowNodes.some((node) => node.id === edge.target)
        );

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load nodes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflow();
  }, [workflowId]);

  const findFlowNode = useCallback(
    (nodeId: string) => nodes.find((node) => node.id === nodeId),
    [nodes]
  );

  const isValidConnection = useCallback(
    (connection: Edge | Connection) => {
      if (!connection.source || !connection.target) {
        return false;
      }

      // Prevent self-loops
      if (connection.source === connection.target) {
        return false;
      }

      const sourceNode = nodes.find((node) => node.id === connection.source);
      const targetNode = nodes.find((node) => node.id === connection.target);

      if (!sourceNode || !targetNode) {
        return false;
      }

      // Prevent duplicate edges
      if (edges.some((edge) => 
        edge.source === connection.source && edge.target === connection.target
      )) {
        return false;
      }

      return true;
    },
    [nodes, edges]
  );

  const onConnect = useCallback(
    async (params: Connection) => {
      if (!isValidConnection(params)) {
        setError("Invalid connection. Cannot create duplicate edges or self-loops.");
        return;
      }

      if (!params.source || !params.target) {
        return;
      }

      const sourceNode = findFlowNode(params.source);
      const targetNode = findFlowNode(params.target);

      if (!sourceNode || !targetNode) {
        return;
      }

      const fromNodeId = sourceNode.data?.backendId as number | undefined;
      const toNodeId = targetNode.data?.backendId as number | undefined;

      if (!fromNodeId || !toNodeId) {
        return;
      }

      setError(null);
      try {
        const created = (await createEdge(workflowId, {
          from_node_id: fromNodeId,
          to_node_id: toNodeId,
        })) as BackendEdge;

        setBackendEdges((prev) => [...prev, created]);
        setEdges((eds) =>
          addEdge(
            {
              id: `edge-${created.id}`,
              source: params.source,
              target: params.target,
            },
            eds
          )
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create edge");
      }
    },
    [findFlowNode, isValidConnection, setEdges, workflowId]
  );

  const handleCreateNode = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!nodeText.trim()) {
      setError("Text is required");
      return;
    }

    if (
      nodeType === "trigger" &&
      backendNodes.some(
        (node) => node.node_type === "trigger" && node.text === nodeText.trim()
      )
    ) {
      setError("Trigger node with this text already exists");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await createNode(workflowId, {
        node_type: nodeType,
        text: nodeText.trim(),
        bot_message: nodeBotMessage.trim() || null,
      });
      setNodeText("");
      setNodeBotMessage("");
      setShowCreateForm(false);
      await loadWorkflow();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create node");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteNode = async (backendId: number) => {
    if (!confirm("Are you sure you want to delete this node?")) {
      return;
    }
    setError(null);
    try {
      await deleteNode(backendId);
      await loadWorkflow();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete node");
    }
  };

  const handleDeleteEdges = async (deletedEdges: Edge[]) => {
    const edgeIds = deletedEdges
      .map((edge) => edge.id)
      .filter((id): id is string => typeof id === "string")
      .map((id) => (id.startsWith("edge-") ? Number(id.slice(5)) : null))
      .filter((id): id is number => Number.isFinite(id));

    if (edgeIds.length === 0) {
      return;
    }

    try {
      await Promise.all(edgeIds.map((edgeId) => deleteEdge(edgeId)));
      setBackendEdges((prev) => prev.filter((edge) => !edgeIds.includes(edge.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete edge");
    }
  };

  // Save node position when user stops dragging
  const handleNodeDragStop = useCallback(
    async (_event: React.MouseEvent, node: FlowNode) => {
      const backendId = node.data?.backendId as number | undefined;
      if (!backendId) return;

      try {
        // Save position to database
        await updateNode(backendId, {
          position_x: Math.round(node.position.x),
          position_y: Math.round(node.position.y),
        });
      } catch (err) {
        console.error("Failed to save node position:", err);
        // Don't show error to user - position save is non-critical
      }
    },
    []
  );

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      const d = node.data as NodeData;
      setSelectedNode({
        backendId: d.backendId,
        type: node.type === "triggerNode" ? "trigger" : "response",
        text: d.text,
        bot_message: d.bot_message ?? "",
      });
    },
    []
  );

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative", background: "#f8fafc" }}>
      {/* Top Bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "60px",
          background: "#ffffff",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          zIndex: 10,
          boxShadow: "0 1px 3px rgba(99,102,241,0.06)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button
            onClick={() => router.back()}
            style={{
              padding: "7px 14px",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              background: "#f8fafc",
              color: "#475569",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: "500",
            }}
          >
            ← Back
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366f1, #4338ca)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
              }}
            >
              🔀
            </div>
            <h1 style={{ fontSize: "16px", fontWeight: "700", margin: 0, color: "#1e293b" }}>
              Workflow Builder
            </h1>
          </div>
        </div>

        <button
          onClick={() => { setShowCreateForm(!showCreateForm); setSelectedNode(null); }}
          style={{
            padding: "8px 16px",
            background: "linear-gradient(135deg, #6366f1, #4f46e5)",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: "600",
            boxShadow: "0 2px 8px rgba(99,102,241,0.3)",
          }}
        >
          + Add Node
        </button>
      </div>

      {/* Create Node Form */}
      {showCreateForm && (
        <div
          style={{
            position: "absolute",
            top: "70px",
            right: "20px",
            width: "320px",
            background: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            padding: "20px",
            boxShadow: "0 8px 30px rgba(99,102,241,0.12), 0 2px 8px rgba(0,0,0,0.06)",
            zIndex: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 7,
                background: "#eef2ff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
              }}
            >
              ➕
            </div>
            <h3 style={{ margin: 0, fontSize: "14px", fontWeight: "700", color: "#1e293b" }}>
              Create New Node
            </h3>
          </div>
          <form onSubmit={handleCreateNode}>
            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.8px", textTransform: "uppercase", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                Node Type
              </label>
              <select
                value={nodeType}
                onChange={(e) => setNodeType(e.target.value as "trigger" | "response")}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "13px",
                  background: "#f8fafc",
                  color: "#1e293b",
                  outline: "none",
                }}
              >
                <option value="trigger">Trigger (Entry Point)</option>
                <option value="response">Action (Response)</option>
              </select>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.8px", textTransform: "uppercase", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                {nodeType === "trigger" ? "Trigger Label" : "Button Name"}
              </label>
              <input
                type="text"
                value={nodeText}
                onChange={(e) => setNodeText(e.target.value)}
                placeholder={nodeType === "trigger" ? "e.g., greeting" : "e.g., hi"}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "13px",
                  background: "#f8fafc",
                  color: "#1e293b",
                  boxSizing: "border-box",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.8px", textTransform: "uppercase", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                Bot Message
              </label>
              <textarea
                value={nodeBotMessage}
                onChange={(e) => setNodeBotMessage(e.target.value)}
                placeholder="e.g., Hello! How can I help you today?"
                rows={3}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  fontSize: "13px",
                  background: "#f8fafc",
                  color: "#166534",
                  resize: "vertical",
                  boxSizing: "border-box",
                  fontFamily: "inherit",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="submit"
                disabled={submitting}
                style={{
                  flex: 1,
                  padding: "9px",
                  background: submitting ? "#a5b4fc" : "linear-gradient(135deg, #6366f1, #4f46e5)",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  cursor: submitting ? "not-allowed" : "pointer",
                  fontSize: "13px",
                  fontWeight: "600",
                  boxShadow: submitting ? "none" : "0 2px 8px rgba(99,102,241,0.3)",
                }}
              >
                {submitting ? "Creating..." : "Create"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  setNodeText("");
                  setNodeBotMessage("");
                  setError(null);
                }}
                style={{
                  padding: "9px 14px",
                  background: "#f8fafc",
                  color: "#64748b",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "13px",
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div
          style={{
            position: "absolute",
            top: "70px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "#fff1f2",
            color: "#be123c",
            padding: "10px 18px",
            borderRadius: "8px",
            border: "1px solid #fecdd3",
            zIndex: 20,
            fontSize: "13px",
            fontWeight: "500",
            boxShadow: "0 2px 8px rgba(190,18,60,0.1)",
          }}
        >
          {error}
        </div>
      )}

      {/* Bot Response Side Panel */}
      {selectedNode && (
        <div
          style={{
            position: "absolute",
            top: "70px",
            right: "20px",
            width: "300px",
            background: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            overflow: "hidden",
            boxShadow: "0 8px 30px rgba(99,102,241,0.12), 0 2px 8px rgba(0,0,0,0.06)",
            zIndex: 15,
          }}
        >
          {/* Panel header */}
          <div
            style={{
              background: selectedNode.type === "trigger" ? "#eef2ff" : "#f8fafc",
              borderBottom: "1px solid #e2e8f0",
              padding: "11px 14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 7,
                  background: selectedNode.type === "trigger"
                    ? "linear-gradient(135deg, #6366f1, #4338ca)"
                    : "linear-gradient(135deg, #64748b, #475569)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 13,
                }}
              >
                {selectedNode.type === "trigger" ? "⚡" : "💬"}
              </div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: selectedNode.type === "trigger" ? "#4338ca" : "#475569",
                }}
              >
                {selectedNode.type === "trigger" ? "Trigger Node" : "Action Node"}
              </span>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                background: "transparent",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: 18,
                lineHeight: 1,
                padding: "0 4px",
              }}
            >
              ×
            </button>
          </div>

          {/* Node label */}
          <div style={{ padding: "12px 14px 0" }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: 0.8, textTransform: "uppercase", color: "#94a3b8", marginBottom: 4 }}>
              {selectedNode.type === "trigger" ? "Trigger Label" : "Button Name"}
            </div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#1e293b",
                background: "#eef2ff",
                border: "1px solid #c7d2fe",
                borderRadius: 7,
                padding: "6px 10px",
              }}
            >
              {selectedNode.text}
            </div>
          </div>

          {/* Bot message */}
          <div style={{ padding: "12px 14px 14px" }}>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: 0.8, textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>
              Bot Response
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #6366f1, #4f46e5)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  flexShrink: 0,
                  boxShadow: "0 2px 8px rgba(99,102,241,0.3)",
                }}
              >
                🤖
              </div>
              <div
                style={{
                  background: selectedNode.bot_message ? "#f0fdf4" : "#f8fafc",
                  border: `1px solid ${selectedNode.bot_message ? "#bbf7d0" : "#e2e8f0"}`,
                  borderRadius: "0 10px 10px 10px",
                  padding: "9px 12px",
                  fontSize: 13,
                  color: selectedNode.bot_message ? "#166534" : "#94a3b8",
                  lineHeight: 1.5,
                  flex: 1,
                  fontStyle: selectedNode.bot_message ? "normal" : "italic",
                }}
              >
                {selectedNode.bot_message || "No bot message set"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* React Flow Canvas */}
      <div style={{ width: "100%", height: "100%", paddingTop: "60px" }}>
        {loading ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: "100%",
              fontSize: "15px",
              color: "#6366f1",
              background: "#f8fafc",
            }}
          >
            Loading workflow...
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={handleNodeDragStop}
            onNodeClick={handleNodeClick}
            isValidConnection={isValidConnection}
            onEdgesDelete={handleDeleteEdges}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Controls
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              }}
            />
            <MiniMap
              nodeColor="#6366f1"
              maskColor="rgba(241,245,249,0.7)"
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
              }}
            />
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="#cbd5e1"
            />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
