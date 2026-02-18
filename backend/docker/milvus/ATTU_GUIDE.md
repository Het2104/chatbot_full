# Attu - Milvus Web UI Guide

## What is Attu?

Attu is the official web-based management interface for Milvus. It allows you to:
- 📊 **Browse Collections**: View all your collections and their schemas
- 🔍 **Inspect Vectors**: See individual vectors and their embeddings
- 📝 **View Chunks**: Browse your document chunks with metadata
- 🔧 **Manage Data**: Query, insert, and delete vectors
- 📈 **Monitor Performance**: Check collection statistics and indexes

## Access Attu

**URL**: http://localhost:3001

No login required! The UI connects automatically to your local Milvus instance.

## Quick Start Guide

### 1. Connect to Milvus
When you first open Attu, you should see:
- **Milvus Address**: Already set to `milvus-standalone:19530`
- Click **Connect** (or it may connect automatically)

### 2. View Your RAG Collection
1. On the left sidebar, click **Collections**
2. Find and click on **rag_chunks** collection
3. You'll see:
   - Collection schema (fields: id, embedding, text, metadata, etc.)
   - Number of entities (total chunks stored)
   - Index information (IVF_FLAT on embedding field)

### 3. Browse Your Document Chunks
1. Inside the **rag_chunks** collection, click the **Data** tab
2. You'll see a table with your chunks:
   - **id**: Unique chunk identifier
   - **embedding**: Vector representation (384 dimensions) - shown as array
   - **text**: The actual text content from your PDFs
   - **metadata**: Source information (filename, page, chunk_index)
   - **timestamp**: When the chunk was added

### 4. Search for Specific Content
1. Click the **Query** tab
2. Use Filter Expression to search, for example:
   ```
   text like "%Theory X%"
   ```
3. Or search by metadata:
   ```
   metadata["source"] like "McGregor%"
   ```
4. Click **Query** to see results

### 5. View Collection Statistics
1. Click the **Overview** tab
2. See:
   - Total entities (chunks)
   - Collection size
   - Index type and parameters
   - Field descriptions

## Understanding the Data

### Embedding Field
- **Type**: FLOAT_VECTOR (384 dimensions)
- **Index**: IVF_FLAT with IP (Inner Product) metric
- **Purpose**: Mathematical representation of text for semantic search
- **Example**: `[0.123, -0.456, 0.789, ...]` (384 numbers between -1 and 1)

### Text Field
- **Type**: VARCHAR (up to 8000 characters)
- **Purpose**: Original text content from PDF
- **Example**: "Theory X assumes that employees are inherently lazy..."

### Metadata Field
- **Type**: JSON
- **Purpose**: Store source information
- **Example**:
  ```json
  {
    "source": "McGregor_Theory_X_and_Y.pdf",
    "page": 3,
    "chunk_id": "chunk_000001",
    "chunk_index": 0,
    "total_chunks": 1
  }
  ```

## Common Tasks

### Check How Many Chunks You Have
1. Go to Collections → rag_chunks
2. Look at **Entities** count in the Overview tab

### Find Chunks from a Specific PDF
1. Go to Data tab
2. Click **Filter**
3. Enter: `metadata["source"] == "your_filename.pdf"`
4. Click Apply

### View Recent Additions
1. Go to Data tab
2. Sort by **timestamp** (descending)
3. See newest chunks first

### Delete All Chunks (Start Fresh)
1. Go to Collections
2. Click the **...** menu next to rag_chunks
3. Select **Drop Collection**
4. Re-run your offline pipeline to rebuild

## Performance Monitoring

### Check Index Status
- Collections → rag_chunks → Overview → Index Information
- Verify IVF_FLAT index is built (status: Built)

### View Collection Size
- Collections → rag_chunks → Overview
- Check disk space used by vectors

## Troubleshooting

### Can't Connect to Milvus
- Ensure Docker services are running: `.\status.bat`
- Check Milvus is healthy in the status output
- Try refreshing the browser

### No Collections Visible
- Run the offline pipeline first to create rag_chunks collection
- Check if you've added any PDFs to be processed

### Chunks Look Wrong
- Check the **text** field - should be readable content
- Check **metadata** - should have source filename
- Check **embedding** - should be array of 384 floats

## Tips for RAG Development

### Verify Chunking Quality
1. Browse through chunks in Data tab
2. Check if text is split logically at sentence boundaries
3. Verify chunks don't exceed 2000 characters
4. Ensure no duplicate chunks (check by sorting by text)

### Test Embeddings
1. Query tab → Vector Search
2. Paste a sample question's embedding
3. Set TopK=5 to find 5 most similar chunks
4. Verify results make semantic sense

### Monitor Growth
- Check entity count before/after adding PDFs
- Calculate: entities / PDFs = average chunks per document
- For 10-page PDFs, expect ~5-15 chunks typically

## Next Steps

1. ✅ Browse your existing chunk from McGregor PDF
2. 📄 Add more PDFs using the offline pipeline
3. 🔍 Use Query tab to test semantic search manually
4. 📊 Monitor collection growth as you add documents
5. 🧪 Compare Attu results with your RAG chatbot responses

## Learn More

- **Attu Documentation**: https://github.com/zilliztech/attu
- **Milvus Documentation**: https://milvus.io/docs
- **Collection Management**: https://milvus.io/docs/manage-collections.md

---

**Current Status:**
- ✅ Attu running on http://localhost:3001
- ✅ Connected to Milvus at localhost:19530
- ✅ rag_chunks collection with 1 chunk from McGregor PDF
- ⏱️ Ready to explore and add more documents!
