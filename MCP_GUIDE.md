# MCP (Model Context Protocol) — Complete Guide for Your Chatbot Project

---

## Table of Contents

1. [What is MCP?](#1-what-is-mcp)
2. [Why MCP was Created](#2-why-mcp-was-created)
3. [How MCP Works — The Core Concept](#3-how-mcp-works--the-core-concept)
4. [MCP Architecture — Hosts, Clients, Servers](#4-mcp-architecture--hosts-clients-servers)
5. [The 4 Primitives of MCP](#5-the-4-primitives-of-mcp)
6. [Transport Layers — How Data Travels](#6-transport-layers--how-data-travels)
7. [What MCP Will Do to YOUR Project](#7-what-mcp-will-do-to-your-project)
8. [What You Can Build with MCP in This Project](#8-what-you-can-build-with-mcp-in-this-project)
9. [MCP Server vs MCP Client — Your Role](#9-mcp-server-vs-mcp-client--your-role)
10. [Real-World Flow in Your Chatbot](#10-real-world-flow-in-your-chatbot)
11. [What Changes in Your Architecture](#11-what-changes-in-your-architecture)
12. [MCP vs What You Have Now](#12-mcp-vs-what-you-have-now)
13. [Security Considerations](#13-security-considerations)
14. [Limitations of MCP](#14-limitations-of-mcp)
15. [What to Implement First](#15-what-to-implement-first)
16. [Glossary](#16-glossary)

---

## 1. What is MCP?

**MCP (Model Context Protocol)** is an open standard created by Anthropic (the company behind Claude AI) in late 2024.

It is a **communication protocol** — a set of rules — that defines how AI models (like Claude, GPT, or any LLM) can connect to external systems, tools, databases, and services in a structured, safe, and predictable way.

Think of it like **USB for AI**. Just as USB standardized how any device connects to any computer, MCP standardizes how any AI model connects to any external data source or capability.

Before MCP, every AI app had to build its own custom integrations — custom code to connect the LLM to your database, your files, your APIs. Every integration was different. MCP eliminates this by providing one universal protocol that both AI models and external systems can speak.

**In one sentence:** MCP lets an AI model ask your systems for information and execute actions, through a standardized interface, without you writing a new custom integration every time.

---

## 2. Why MCP was Created

### The Problem Before MCP

Imagine you are building an AI assistant for your company using Claude or GPT. You want the AI to:
- Search your company documents
- Check your database for customer info
- Look up an FAQ entry
- Send an email
- Execute a workflow

Before MCP, you had to:
- Write custom code in your app to call each service
- Re-implement this for every new AI model or framework
- Manually handle errors, retries, auth, schemas for each
- Nothing was reusable — every company built the same wheel differently

### The MCP Solution

MCP defines a single standard so that:
- You build **one MCP Server** that wraps your services
- **Any MCP-compatible AI client** (Claude Desktop, VS Code Copilot, your own app) can connect to it
- The AI model knows exactly how to discover your tools and call them
- You never have to re-implement this for a different AI model

It is the same reason HTTP became the standard for web communication — one protocol, every browser and server speaks it.

---

## 3. How MCP Works — The Core Concept

MCP is a **client-server protocol** based on **JSON-RPC 2.0**.

Here is the fundamental flow:

```
AI Model / LLM (the "brain")
        │
        │  "I need to search the knowledge base"
        ▼
  MCP Client (the connector in your app)
        │
        │  JSON-RPC request: { method: "tools/call", params: { name: "search_knowledge_base", arguments: { query: "refund policy" } } }
        ▼
  MCP Server (YOUR server — wraps your services)
        │
        │  Calls your RAG pipeline / Milvus / FAQ cache
        ▼
  Returns structured result back to AI Model
        │
        ▼
  AI Model uses the result to generate a final answer
```

### The Key Insight

The AI model does NOT directly call your database, your API, or your service. It talks to the **MCP Server**, which acts as a secure, structured intermediary. The MCP Server decides what to expose and what to protect.

### The Lifecycle of One Request

1. **Discovery** — The MCP client asks the server: "What tools do you have?" Server responds with a list of available tools, their names, descriptions, and input schemas.
2. **Decision** — The LLM reads the user's message and decides which tool to call based on the descriptions.
3. **Invocation** — The LLM sends a tool call request with arguments.
4. **Execution** — The MCP Server runs the actual code (queries Milvus, checks Redis, etc.).
5. **Response** — The result is returned to the LLM.
6. **Generation** — The LLM uses the result to form a final answer to the user.

---

## 4. MCP Architecture — Hosts, Clients, Servers

MCP has three distinct roles:

### Host
The **Host** is the application that the user interacts with — the thing that contains the AI model.

Examples of Hosts:
- Claude Desktop (Anthropic's app)
- VS Code with GitHub Copilot
- Your own Next.js chatbot frontend
- A command-line AI assistant

The Host is responsible for launching and managing connections to MCP Servers.

### Client
The **Client** lives inside the Host. It is the code module that speaks the MCP protocol. Each Client maintains exactly **one connection** to one MCP Server.

If a Host connects to 3 MCP Servers, it has 3 Clients — one per connection.

### Server
The **Server** is what **YOU will build**. It is a lightweight service that:
- Exposes your data, tools, and capabilities
- Responds to MCP requests from the AI
- Can be local (runs on the same machine) or remote (runs on a cloud server)

In your case, your MCP Server will wrap your: RAG pipeline, FAQ service, Chatbot API, and Milvus vector store.

```
┌─────────────────────────────────────┐
│              HOST                    │
│  (Claude Desktop / Your App)         │
│                                      │
│  ┌─────────┐     ┌─────────┐        │
│  │Client 1 │     │Client 2 │        │
│  └────┬────┘     └────┬────┘        │
└───────│───────────────│─────────────┘
        │               │
        ▼               ▼
   MCP Server 1    MCP Server 2
   (Your Chatbot)  (External Tool)
```

---

## 5. The 4 Primitives of MCP

MCP exposes 4 types of capabilities from a server. These are called **primitives**.

---

### Primitive 1: Tools

**What they are:** Functions the AI can call to perform an action or retrieve data.

**Who controls them:** The AI model (LLM) decides when to call a tool.

**Examples you can build for your project:**
- `search_knowledge_base(chatbot_id, query)` — RAG search over indexed PDFs and URLs
- `lookup_faq(chatbot_id, question)` — check the FAQ cache in Redis
- `list_chatbots()` — return all available chatbots
- `get_workflow(chatbot_id)` — return the conversation workflow structure
- `ask_chatbot(chatbot_id, message)` — send a full message and get a response
- `get_chat_history(session_id)` — retrieve past messages

Tools are the **most important primitive** and what you will implement first.

---

### Primitive 2: Resources

**What they are:** Data sources the AI can read — like files, documents, database records.

**Who controls them:** The **Host/user** decides which resources to attach to a conversation (not the AI automatically).

**Examples you can build:**
- `chatbot://1/knowledge_base` — all indexed documents for chatbot #1
- `chatbot://1/faqs` — the full FAQ list for chatbot #1
- `session://42/history` — full conversation history for session 42

Resources are like **attachments** or **context documents** that the user can hand to the AI. The AI reads them but does not invoke them like tools.

---

### Primitive 3: Prompts

**What they are:** Pre-built prompt templates that users can select and invoke. They can accept arguments and produce structured messages.

**Who controls them:** The **user** selects which prompt to use.

**Examples you can build:**
- `answer_with_knowledge(chatbot_id)` — a system prompt telling the AI how to behave when answering with your knowledge base
- `onboarding_flow(chatbot_id)` — a guided prompt that walks users through a chatbot's workflow
- `summarize_chat(session_id)` — a prompt that asks the AI to summarize a conversation

---

### Primitive 4: Sampling

**What they are:** Lets your MCP Server **ask the host's LLM** to generate text on your server's behalf.

**Who controls them:** Your Server requests a generation, the Host executes it.

**Example:** Your server needs to summarize a retrieved document before returning it. Instead of calling Groq internally, it asks the host's Claude to do it.

This is the most advanced primitive. You will not need it initially.

---

## 6. Transport Layers — How Data Travels

MCP supports different transport mechanisms for sending data between client and server:

### stdio (Standard Input/Output)
- Used for **local servers** running on the same machine
- The Host launches your MCP Server as a child process
- Communication happens via stdin/stdout pipes
- Best for: Claude Desktop integration, local development
- Simple, no network required

### SSE (Server-Sent Events)
- Used for **remote servers** running over HTTP
- One-way stream from server to client for responses
- Uses regular HTTP POST for client-to-server messages
- Best for: deployed web servers, your FastAPI backend

### Streamable HTTP (newest standard)
- Uses HTTP POST with optional streaming
- Most flexible for production web deployments
- Supports both streaming and non-streaming responses
- Best for: your production deployment behind FastAPI

### Which to use for your project:
- **Development / Claude Desktop:** stdio
- **Production / your Next.js app connecting:** Streamable HTTP via FastAPI

---

## 7. What MCP Will Do to YOUR Project

This section explains the concrete impact on your existing chatbot platform.

### Before MCP (Your Current State)

Your project currently works like this:

```
User types message in browser
        ↓
FastAPI receives POST /chat/message
        ↓
ChatService checks: Workflow → FAQ → RAG → Default
        ↓
Response sent back to browser
```

The knowledge base is only accessible through your own chat interface. Nothing outside your app can query it. The LLM (Groq) is a passive generator — it never decides what information to look for.

### After MCP (New Capabilities)

**1. Your knowledge base becomes accessible to ANY MCP-compatible AI tool**

Claude Desktop, VS Code Copilot, any future MCP client can directly query your chatbot's knowledge base. Your company's documents become universally accessible to AI tools.

**2. The LLM becomes an active agent**

Instead of always following the same Workflow → FAQ → RAG path, the LLM itself can decide: "I need to search the knowledge base" or "I should check the FAQ first" or "I need to get the workflow for this chatbot" — and call the appropriate tool.

**3. Your backend gains a new interface**

Alongside your REST API, your backend now also speaks MCP. External AI tools can discover and use your capabilities without you building custom integrations for each.

**4. Multi-step reasoning becomes possible**

With tools, the LLM can chain multiple calls: search docs → find related FAQ → combine both into a comprehensive answer. This is impossible with your current single-pass RAG.

---

## 8. What You Can Build with MCP in This Project

Here are the specific things you can add, grouped by category:

### Knowledge & Search Tools
- Search your Milvus vector store with natural language
- Look up specific FAQs by question
- Filter search by specific chatbot or document type
- Return source metadata (which PDF, which page, which URL)

### Chatbot Management Tools
- List all available chatbots
- Get the workflow/conversation tree for any chatbot
- Get chatbot configuration and settings
- Create or modify FAQs via natural language

### Session & History Tools
- Retrieve chat history for a session
- Summarize past conversations
- Look up what a user has asked before
- Transfer context between sessions

### Admin Tools (admin role only)
- Trigger PDF re-indexing
- Add new URLs to the knowledge base
- View indexing status
- Get analytics on most-asked questions

### Resources You Can Expose
- All indexed documents for a chatbot
- FAQ database as a browsable resource
- Workflow structure as a readable document
- System configuration overview

### Prompts You Can Provide
- "Answer as customer support for [company]" — with the right context loaded
- "Summarize this chatbot's knowledge base"
- "Find gaps in the knowledge base given this conversation"

---

## 9. MCP Server vs MCP Client — Your Role

You will be building an **MCP Server**. It is important to understand the difference.

### You ARE building: MCP Server
Your server wraps your existing services and exposes them. It:
- Registers what tools are available
- Receives tool call requests
- Executes the real logic (queries Milvus, Redis, PostgreSQL)
- Returns structured results

You write the server once. Any MCP-compatible tool in the world can then use it.

### You are NOT (initially) building: MCP Client
An MCP Client is built into AI applications. Claude Desktop already has an MCP Client built in. VS Code Copilot has one. You do NOT need to build a client to connect to your own server — you just point existing clients at your server.

HOWEVER — you could also add an MCP Client to your own Next.js frontend or FastAPI backend if you want your chatbot to query other MCP servers (e.g., an external MCP server for weather, calendar, Slack, etc.).

---

## 10. Real-World Flow in Your Chatbot

Here is a concrete example of what happens after MCP is added:

### Scenario: User asks "What is your refund policy, and how long does it take?"

**Without MCP (current behavior):**
1. ChatService checks workflow → no match
2. Checks FAQ cache → no match  
3. Calls RAG → searches Milvus → gets top-5 chunks → sends to Groq with context
4. Groq generates an answer based only on those 5 chunks
5. Returns answer

**With MCP Tool Calling (after implementation):**
1. User message sent to LLM
2. LLM decides: "I need to search the knowledge base for refund policy"
3. LLM calls tool: `search_knowledge_base("refund policy")`
4. MCP Server queries Milvus → returns relevant chunks with sources
5. LLM reads results, decides: "I also need to check the FAQ for refund timeframes"
6. LLM calls tool: `lookup_faq("refund timeframe")`
7. MCP Server checks Redis FAQ cache → returns FAQ entry
8. LLM now has both pieces of information
9. LLM generates a comprehensive answer citing both sources
10. Returns answer with source citations

The LLM drives the retrieval process instead of following a fixed path.

---

## 11. What Changes in Your Architecture

### New Component Added
A new service `backend/app/mcp_server/` will be added alongside your existing services. It is a separate process that runs next to FastAPI.

### Nothing Gets Removed
Your existing REST API, WebSocket, RabbitMQ queue, RAG pipeline — all remain unchanged. MCP is **additive only**.

### Your Existing Services Become Reusable
Your `ChatService`, `RedisCacheService`, and Milvus store — which you already built — become the backend for your MCP tools. No duplication. MCP tools just call these same services.

### Two Ways Users Can Now Access Your Knowledge Base

```
BEFORE:
  Browser → Next.js → FastAPI → ChatService → Knowledge Base

AFTER:
  Browser → Next.js → FastAPI → ChatService → Knowledge Base
                                                    ↑
  Claude Desktop → MCP Client → MCP Server ─────────┘
  VS Code Copilot → MCP Client → MCP Server ─────────┘
  Custom AI Agent → MCP Client → MCP Server ─────────┘
```

---

## 12. MCP vs What You Have Now

| Capability | Current System | With MCP |
|---|---|---|
| Knowledge access | Only via your chat UI | Any MCP-compatible AI tool |
| LLM retrieval strategy | Fixed waterfall (Workflow → FAQ → RAG) | LLM decides dynamically |
| Multi-step reasoning | Not possible | LLM chains multiple tool calls |
| Source citations | Not surfaced | Built into every tool result |
| External AI tools | Cannot use your data | Can directly query knowledge base |
| Custom AI agents | Must use your API | Can use your tools natively |
| FAQ lookup | Redis cache only | Exposed as tool + resource |
| Workflow | Hard-coded graph | Queryable and inspectable |
| Admin operations | Only via REST API | Triggerable via AI tool call |

---

## 13. Security Considerations

MCP introduces new security surface. These are the things you must think about before deploying:

### Authentication
MCP itself does not define authentication — it leaves that to you. You must decide:
- Who is allowed to connect to your MCP Server?
- Is it public (anyone can use your knowledge base) or private (only your team)?
- For local stdio transport: anyone with machine access can connect
- For HTTP transport: you need API keys or OAuth

### Authorization
Your existing RBAC (admin vs user roles) must be enforced inside each tool handler. An MCP client calling `upload_document` should be rejected unless it provides admin credentials.

### Tool Scope
Each tool should do exactly one thing and expose only what is necessary. Do not create a tool that returns raw database records. Return only the fields needed.

### Input Validation
Even though MCP defines schemas, always validate tool arguments inside your tool handlers, just as you would validate REST API inputs. Treat MCP inputs as external/untrusted.

### Rate Limiting
Your MCP Server should enforce rate limits. Without them, a misconfigured AI client could call `search_knowledge_base` thousands of times per minute.

### Sensitive Data
Your knowledge base may contain sensitive documents. The MCP Server should respect the same document-level access controls as your REST API.

---

## 14. Limitations of MCP

These are things MCP does NOT solve and you should not expect from it:

### Not a Replacement for Your REST API
MCP is not an API for human users. It is specifically for AI models. Your frontend still needs the REST API.

### Not Stateful by Default
MCP connections are generally stateless. There is no concept of "session continuity" built into MCP itself — you manage state in your own services (like you already do with Redis).

### Not a Streaming Protocol for Large Data
MCP is designed for tool calls that return structured data quickly. It is not designed to stream large files or real-time event streams to an AI (though streaming responses are supported for text generation via the Sampling primitive).

### Model Must Support Tool Calling
Not all LLMs support tool calling. Your current model (llama3-8b-8192 via Groq) has limited tool calling support. For reliable tool use, you would upgrade to `llama-3.3-70b-versatile` or `Claude 3.5 Sonnet`.

### MCP Server Must Be Reachable
For remote deployment, your MCP Server must be publicly accessible (with auth). For local Claude Desktop, it only works on the same machine.

### No Automatic Discovery
There is no central registry of MCP servers (yet). You manually configure which servers a client connects to. Claude Desktop, for example, requires you to edit a config file to add your server.

---

## 15. What to Implement First

Based on your project's current state, here is a clear implementation order:

### Step 1 — Build the MCP Server skeleton
Set up the server with the `fastmcp` Python library. No tools yet, just the server structure that can start and respond to `initialize` requests. Verify Claude Desktop can connect to it.

### Step 2 — Add the `search_knowledge_base` tool
This is the highest-value tool. Wire it to your existing Milvus retriever. Test it: open Claude Desktop, ask a question about a document you indexed. Claude should call your tool and return source-grounded answers.

### Step 3 — Add the `lookup_faq` tool
Wire to your Redis FAQ cache. Instant FAQ lookup for any AI client.

### Step 4 — Add the `list_chatbots` and `ask_chatbot` tools
Let external AI clients see what chatbots exist and send messages to them.

### Step 5 — Add Resources
Expose your FAQ list and indexed document list as browsable resources. These help AI clients understand what data is available before choosing which tool to call.

### Step 6 — Switch to HTTP transport for production
If you want your Next.js frontend's chat interface to also use MCP tools (instead of the fixed waterfall), move from stdio to Streamable HTTP transport integrated into FastAPI.

### Step 7 — Enable Tool Calling in your RAG pipeline
The biggest architectural upgrade: let Groq's LLM call your MCP tools during chat, replacing the fixed Workflow → FAQ → RAG waterfall with dynamic LLM-driven retrieval.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| MCP | Model Context Protocol — the communication standard |
| Host | The application containing the AI model (e.g., Claude Desktop, your chat app) |
| Client | The MCP module inside the Host that manages one server connection |
| Server | The service YOU build that wraps your data and capabilities |
| Tool | A callable function the AI can invoke (like a function in code) |
| Resource | A readable data source the AI or user can attach to a conversation |
| Prompt | A pre-built template that users can select to guide the AI |
| Sampling | When your server asks the host's AI to generate text |
| JSON-RPC | The underlying message format MCP uses (method + params + id) |
| stdio transport | MCP communication via standard input/output (local only) |
| SSE transport | MCP communication via HTTP + Server-Sent Events (remote) |
| Streamable HTTP | MCP communication via HTTP POST with optional streaming (production) |
| Tool calling | When an LLM decides to call a tool instead of directly generating text |
| Agentic RAG | RAG where the LLM actively decides what to retrieve (vs fixed pipeline) |
| fastmcp | Python library that simplifies building MCP servers |
| BAAI/bge-large-en-v1.5 | Your current embedding model (1024-dim vectors) |
| Milvus | Your vector database storing document embeddings |
| Groq | Your LLM API provider (llama3-8b-8192) |

---

## Summary

MCP gives your chatbot platform a **universal interface** for AI models. Instead of your knowledge base being locked inside your chat UI, it becomes a **tool that any AI can use**.

For your project specifically:
- Your RAG pipeline becomes a tool external AI clients can call
- Your FAQ cache becomes queryable by AI agents
- Your workflow structure becomes inspectable
- The Groq LLM inside your chatbot can start making its own retrieval decisions
- Claude Desktop or VS Code Copilot can search your company documents directly

**You are not replacing anything you built.** You are wrapping it in a new, standardized interface that the wider AI ecosystem speaks natively.

The implementation starts with one file: your MCP Server. Everything else — Milvus, Redis, PostgreSQL, FastAPI — continues to work exactly as it does today.
