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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { MemoTriggerNode, MemoResponseNode } from "./CustomNode";

type BackendNode = {
  id: number;
  node_type: "trigger" | "response";
  text: string;
  position_x?: number | null;
  position_y?: number | null;
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
  const [submitting, setSubmitting] = useState(false);

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

      const flowNodes: FlowNode[] = (backendNodeList as BackendNode[]).map(
        (node, index) => ({
          id: `node-${node.id}`,
          type: node.node_type === "trigger" ? "triggerNode" : "responseNode",
          position: {
            // Use saved position if available, otherwise calculate default
            x: node.position_x ?? 100 + index * 260,
            y: node.position_y ?? 120 + (index % 3) * 200,
          },
          data: {
            text: node.text,
            backendId: node.id,
            onDelete: handleDeleteNode,
          },
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
      });
      setNodeText("");
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

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative" }}>
      {/* Top Bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "60px",
          background: "white",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            onClick={() => router.back()}
            style={{
              padding: "8px 16px",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              background: "white",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            ← Back
          </button>
          <h1 style={{ fontSize: "20px", fontWeight: "600", margin: 0 }}>
            Visual Workflow Editor
          </h1>
        </div>

        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          style={{
            padding: "10px 20px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500",
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
            background: "white",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "20px",
            boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
            zIndex: 10,
          }}
        >
          <h3 style={{ margin: "0 0 16px 0", fontSize: "16px" }}>
            Create New Node
          </h3>
          <form onSubmit={handleCreateNode}>
            <div style={{ marginBottom: "12px" }}>
              <label style={{ fontSize: "13px", fontWeight: "500" }}>
                Node Type
              </label>
              <select
                value={nodeType}
                onChange={(e) => setNodeType(e.target.value as "trigger" | "response")}
                style={{
                  width: "100%",
                  padding: "8px",
                  marginTop: "4px",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  fontSize: "14px",
                  background: "white",
                }}
              >
                <option value="trigger">Trigger (Workflow Entry)</option>
                <option value="response">Response</option>
              </select>
            </div>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ fontSize: "13px", fontWeight: "500" }}>
                {nodeType === "trigger" ? "Trigger Text" : "Response Text"}
              </label>
              <input
                type="text"
                value={nodeText}
                onChange={(e) => setNodeText(e.target.value)}
                placeholder={nodeType === "trigger" ? "e.g., Silver Touch" : "e.g., Please choose an option:"}
                style={{
                  width: "100%",
                  padding: "8px",
                  marginTop: "4px",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  fontSize: "14px",
                }}
              />
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                type="submit"
                disabled={submitting}
                style={{
                  flex: 1,
                  padding: "8px",
                  background: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: submitting ? "not-allowed" : "pointer",
                  fontSize: "14px",
                  fontWeight: "500",
                }}
              >
                {submitting ? "Creating..." : "Create"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  setNodeText("");
                  setError(null);
                }}
                style={{
                  padding: "8px 16px",
                  background: "white",
                  color: "#374151",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px",
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
            background: "#fef2f2",
            color: "#dc2626",
            padding: "12px 20px",
            borderRadius: "6px",
            border: "1px solid #fca5a5",
            zIndex: 10,
            fontSize: "14px",
          }}
        >
          {error}
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
              fontSize: "16px",
              color: "#6b7280",
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
            isValidConnection={isValidConnection}
            onEdgesDelete={handleDeleteEdges}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-left"
          >
            <Controls />
            <MiniMap
              nodeColor="#3b82f6"
              maskColor="rgba(0, 0, 0, 0.1)"
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: "4px",
              }}
            />
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
