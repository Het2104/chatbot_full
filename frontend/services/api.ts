/**
 * API Service Module
 * 
 * Centralizes all HTTP communication with the FastAPI backend.
 * Provides type-safe functions for each API endpoint.
 * 
 * Base URL: http://127.0.0.1:8000
 * All requests use JSON format except file uploads.
 */

const BASE_URL = "http://127.0.0.1:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/**
 * Generic HTTP request function
 * 
 * Handles:
 * - JSON serialization/deserialization
 * - Error responses
 * - Empty responses (204 No Content)
 * 
 * @param path - API endpoint path (e.g., "/chatbots")
 * @param options - Request configuration
 * @returns Parsed JSON response or undefined for 204
 * @throws Error with backend error message or generic error
 */
async function request<T>(
	path: string,
	options: {
		method?: HttpMethod;
		body?: unknown;
	} = {}
): Promise<T> {
	const { method = "GET", body } = options;

	// Make HTTP request
	const response = await fetch(`${BASE_URL}${path}`, {
		method,
		headers: {
			"Content-Type": "application/json",
		},
		body: body === undefined ? undefined : JSON.stringify(body),
	});

	// Handle error responses
	if (!response.ok) {
		const errorText = await response.text().catch(() => "");
		const message = errorText || `Request failed with status ${response.status}`;
		throw new Error(message);
	}

	// Handle empty responses (e.g., DELETE returns 204 No Content)
	if (response.status === 204) {
		return undefined as T;
	}

	// Parse and return JSON
	return (await response.json()) as T;
}

/* ===============================================================
 * CHATBOT MANAGEMENT APIs
 * =============================================================== */

/**
 * Get all chatbots in the system
 * 
 * @returns Array of chatbot objects with id, name, description, created_at
 */
export async function getChatbots() {
	return request("/chatbots");
}

/**
 * Create a new chatbot
 * 
 * @param data - Chatbot data: { name: string, description?: string }
 * @returns Created chatbot with assigned ID
 */
export async function createChatbot(data: unknown) {
	return request("/chatbots", { method: "POST", body: data });
}

/**
 * Delete a chatbot and all related data (workflows, FAQs, sessions)
 * 
 * @param chatbotId - ID of the chatbot to delete
 * @returns undefined (204 No Content)
 */
export async function deleteChatbot(chatbotId: string | number) {
	return request(`/chatbots/${chatbotId}`, { method: "DELETE" });
}

/* ===============================================================
 * FAQ MANAGEMENT APIs
 * =============================================================== */

/**
 * Get FAQs for a chatbot with optional filtering
 * 
 * @param chatbotId - ID of the chatbot
 * @param activeOnly - If true, only return active FAQs
 * @returns Array of FAQ objects
 */
export async function getFAQs(chatbotId: string | number, activeOnly: boolean = false) {
	const params = activeOnly ? "?active_only=true" : "";
	return request(`/chatbots/${chatbotId}/faqs${params}`);
}

/**
 * Get parent-level FAQs only (for initial FAQ display)
 * 
 * @param chatbotId - ID of the chatbot
 * @returns Array of parent FAQ objects (parent_id is null)
 */
export async function getParentFAQs(chatbotId: string | number) {
	return request(`/chatbots/${chatbotId}/faqs?active_only=true&parent_only=true`);
}

/**
 * Create a new FAQ for a chatbot
 * 
 * @param chatbotId - ID of the chatbot
 * @param data - FAQ data: { question, answer, parent_id?, is_active?, display_order? }
 * @returns Created FAQ with assigned ID
 */
export async function createFAQ(chatbotId: string | number, data: unknown) {
	return request(`/chatbots/${chatbotId}/faqs`, {
		method: "POST",
		body: data,
	});
}

/**
 * Update an existing FAQ (partial update)
 * 
 * @param faqId - ID of the FAQ to update
 * @param data - Fields to update (all optional)
 * @returns Updated FAQ object
 */
export async function updateFAQ(faqId: string | number, data: unknown) {
	return request(`/faqs/${faqId}`, {
		method: "PATCH",
		body: data,
	});
}

/**
 * Delete an FAQ permanently
 * 
 * @param faqId - ID of the FAQ to delete
 * @returns undefined (204 No Content)
 */
export async function deleteFAQ(faqId: string | number) {
	return request(`/faqs/${faqId}`, { method: "DELETE" });
}

/* ===============================================================
 * WORKFLOW MANAGEMENT APIs
 * =============================================================== */

/**
 * Get all workflows for a chatbot
 * 
 * @param chatbotId - ID of the chatbot
 * @returns Array of workflow objects
 */
export async function getWorkflows(chatbotId: string | number) {
	return request(`/chatbots/${chatbotId}/workflows`);
}

/**
 * Create a new workflow for a chatbot
 * 
 * @param chatbotId - ID of the chatbot
 * @param data - Workflow data: { name: string }
 * @returns Created workflow (inactive by default)
 */
export async function createWorkflow(chatbotId: string | number, data: unknown) {
	return request(`/chatbots/${chatbotId}/workflows`, {
		method: "POST",
		body: data,
	});
}

/**
 * Activate a workflow (deactivates all other workflows for same chatbot)
 * 
 * @param workflowId - ID of the workflow to activate
 * @returns Activated workflow object
 */
export async function activateWorkflow(workflowId: string | number) {
	// Important: Must use PUT method (idempotent state change)
	return request(`/workflows/${workflowId}/activate`, { method: "PUT" });
}

/**
 * Delete a workflow and all its nodes/edges
 * 
 * @param workflowId - ID of the workflow to delete
 * @returns undefined (204 No Content)
 */
export async function deleteWorkflow(workflowId: string | number) {
	return request(`/workflows/${workflowId}`, { method: "DELETE" });
}

/* ===============================================================
 * NODE MANAGEMENT APIs
 * =============================================================== */

/**
 * Get all nodes in a workflow
 * 
 * @param workflowId - ID of the workflow
 * @returns Array of node objects (triggers and responses)
 */
export async function getNodes(workflowId: string | number) {
	return request(`/workflows/${workflowId}/nodes`);
}

/**
 * Create a new node in a workflow
 * 
 * @param workflowId - ID of the workflow
 * @param data - Node data: { node_type: "trigger" | "response", text: string }
 * @returns Created node with assigned ID
 */
export async function createNode(workflowId: string | number, data: unknown) {
	return request(`/workflows/${workflowId}/nodes`, {
		method: "POST",
		body: data,
	});
}

/**
 * Delete a node (also deletes connected edges)
 * 
 * @param nodeId - ID of the node to delete
 * @returns undefined (204 No Content)
 */
export async function deleteNode(nodeId: string | number) {
	return request(`/nodes/${nodeId}`, { method: "DELETE" });
}

/**
 * Update a node's text or position
 * 
 * Used to:
 * - Update node text content
 * - Save node position when dragged in visual workflow editor
 * 
 * @param nodeId - ID of the node to update
 * @param data - Update data: { text?: string, position_x?: number, position_y?: number }
 * @returns Updated node object
 */
export async function updateNode(nodeId: string | number, data: unknown) {
	return request(`/nodes/${nodeId}`, {
		method: "PATCH",
		body: data,
	});
}

/* ===============================================================
 * EDGE MANAGEMENT APIs
 * =============================================================== */

/**
 * Get all edges in a workflow
 * 
 * @param workflowId - ID of the workflow
 * @returns Array of edge objects with from_node_id and to_node_id
 */
export async function getEdges(workflowId: string | number) {
	return request(`/workflows/${workflowId}/edges`);
}

/**
 * Create a new edge (connect two nodes)
 * 
 * @param workflowId - ID of the workflow
 * @param data - Edge data: { from_node_id: number, to_node_id: number }
 * @returns Created edge with assigned ID
 */
export async function createEdge(workflowId: string | number, data: unknown) {
	return request(`/workflows/${workflowId}/edges`, {
		method: "POST",
		body: data,
	});
}

/**
 * Delete an edge (disconnect two nodes)
 * 
 * @param edgeId - ID of the edge to delete
 * @returns undefined (204 No Content)
 */
export async function deleteEdge(edgeId: string | number) {
	return request(`/edges/${edgeId}`, { method: "DELETE" });
}

/* ===============================================================
 * CHAT CONVERSATION APIs
 * =============================================================== */

/**
 * Start a new chat session
 * 
 * Creates a session and returns all trigger nodes as initial options.
 * 
 * @param chatbotId - ID of the chatbot to chat with
 * @returns Object with: session_id, chatbot_id, trigger_nodes[], started_at
 */
export async function startChat(chatbotId: string | number) {
	return request(`/chat/start`, {
		method: "POST",
		body: { chatbot_id: chatbotId },
	});
}

/**
 * Send a message and receive bot response
 * 
 * Processes message through workflow nodes → FAQs → RAG → default response.
 * 
 * @param sessionId - ID of the current chat session
 * @param message - User's message text
 * @returns Object with: bot_response, options[] (next conversation steps), timestamp
 */
export async function sendMessage(sessionId: string | number, message: string) {
	return request(`/chat/message`, {
		method: "POST",
		body: { session_id: sessionId, message },
	});
}

/* ===============================================================
 * PDF UPLOAD & DOCUMENT MANAGEMENT APIs
 * =============================================================== */

/**
 * Upload a PDF file for RAG (Retrieval Augmented Generation)
 * 
 * The PDF is processed server-side:
 * 1. Text extraction (with OCR fallback for scanned PDFs)
 * 2. Text cleaning and normalization
 * 3. Chunking into smaller segments
 * 4. Vector embedding generation
 * 5. Storage in Milvus vector database
 * 
 * After upload, the PDF content becomes searchable via chat.
 * 
 * @param file - PDF file to upload
 * @returns Object with:
 *   - success: boolean
 *   - message: human-readable result
 *   - filename: sanitized filename
 *   - stats: { num_chunks, processing_time_seconds, text_length, cleaned_length }
 *   - error: error message if failed
 * @throws Error if upload fails or processing fails
 */
export async function uploadPdf(file: File): Promise<{
	success: boolean;
	message: string;
	filename: string;
	stats?: {
		text_length: number;
		cleaned_length: number;
		num_chunks: number;
		processing_time_seconds: number;
	};
	error?: string;
}> {
	// Create form data (multipart/form-data for file upload)
	const formData = new FormData();
	formData.append("file", file);

	// Make request (don't set Content-Type - browser sets it with boundary)
	const response = await fetch(`${BASE_URL}/api/upload/pdf`, {
		method: "POST",
		body: formData,
	});

	// Handle error responses
	if (!response.ok) {
		const errorData = await response.json().catch(() => null);
		throw new Error(errorData?.detail || `Upload failed with status ${response.status}`);
	}

	return await response.json();
}

/**
 * Get list of all indexed PDF documents
 * 
 * Returns metadata about uploaded PDFs (from file system, not vector DB).
 * 
 * @returns Object with:
 *   - pdfs: Array of { filename, size_bytes, size_mb, uploaded_at }
 *   - count: total number of PDFs
 */
export async function getIndexedPdfs(): Promise<{
	pdfs: Array<{
		filename: string;
		size_bytes: number;
		size_mb: number;
		uploaded_at: number;
	}>;
	count: number;
}> {
	return request("/api/upload/pdfs");
}

/**
 * Delete a PDF file
 * 
 * Warning: Only deletes the physical file, NOT the vector embeddings.
 * The document will still be searchable via RAG until vectors are manually removed.
 * 
 * @param filename - Name of the PDF file to delete
 * @returns Object with success message
 */
export async function deletePdf(filename: string) {
	return request(`/api/upload/pdf/${encodeURIComponent(filename)}`, {
		method: "DELETE",
	});
}
