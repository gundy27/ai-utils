# RAG Chatbot v1

Production-quality web application showcasing the complete gundy-ai RAG platform.

## Features

- **Document Upload**: Drag & drop TXT, PDF, DOCX files
- **Smart Chat**: Ask questions about your documents
- **Source Attribution**: See which chunks informed each answer
- **Session Management**: Multi-turn conversations with history
- **Cost Tracking**: Monitor tokens and costs in real-time
- **Analytics Dashboard**: System stats and usage metrics

## Prerequisites

- Node.js >= 18
- Running RAG API backend at `http://localhost:8000`

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Visit application
open http://localhost:3000
```

## Backend Setup

Make sure the RAG API is running:

```bash
cd ../../services/rag-api
cp env.example .env
# Add your OPENAI_API_KEY to .env
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

## Configuration

Edit `.env.local` if your API is running on a different URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Usage

### 1. Upload Documents

Click or drag-and-drop to upload:

- TXT files
- PDF documents
- DOCX files
- Markdown, CSV, logs

The system will:

- Extract text from the document
- Split into semantic chunks
- Generate embeddings
- Store in vector database
- Show you chunks created, tokens used, and cost

### 2. Chat with Your Documents

Ask questions like:

- "What is this document about?"
- "Summarize the main points"
- "What does it say about [topic]?"

The chatbot will:

- Search for relevant chunks
- Show source citations with similarity scores
- Generate contextualized answers
- Maintain conversation history

### 3. Multi-turn Conversations

Continue the conversation:

- Follow-up questions use conversation context
- Switch between sessions in the sidebar
- Create new sessions for fresh topics

### 4. Monitor Performance

The stats panel shows:

- Total cost and tokens for current session
- System-wide document and vector counts
- Embedding model and configuration
- Supported file types

## Architecture

### Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript
- **Styling**: Tailwind CSS
- **Backend**: FastAPI RAG API (separate service)

### Component Structure

```
app/
├── layout.tsx          - Root layout
├── page.tsx            - Main application
└── globals.css         - Tailwind styles

components/
├── DocumentUpload.tsx  - Drag & drop upload
├── ChatInterface.tsx   - Chat UI with messages
├── MessageBubble.tsx   - Individual message rendering
├── SourceCitation.tsx  - Source display with scores
├── SessionSidebar.tsx  - Session management
└── StatsPanel.tsx      - Analytics dashboard

lib/
├── api.ts              - API client
└── types.ts            - TypeScript types
```

## Development

```bash
# Run with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm run start
```

## Troubleshooting

**"Failed to fetch" errors**:

- Ensure RAG API is running on `http://localhost:8000`
- Check CORS settings in backend config
- Verify OPENAI_API_KEY is set in backend `.env`

**No documents in chat**:

- Upload a document first
- Wait for processing to complete
- Check backend logs for errors

**Session not persisting**:

- Backend uses SQLite for metadata (persists across restarts)
- Session IDs are tracked in metadata store

## Components Demonstrated

This UI showcases all gundy-ai libraries built today:

1. **gundy-ai-extractors**: Document parsing (TXT, PDF, DOCX)
2. **gundy-ai-chunker**: Token-aware text splitting
3. **gundy-ai-embeddings**: OpenAI embeddings with cost tracking
4. **gundy-ai-vectorstore**: ChromaDB semantic search
5. **gundy-ai-metadata-store**: Session and conversation management
6. **gundy-ai-llm**: OpenAI chat completion

## License

See main ai-utils repository.
