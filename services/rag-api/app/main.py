"""RAG API main application."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .models import (
    ChatRequest,
    ChatResponse,
    DocumentIngestResponse,
    HealthResponse,
    LeadCapturePrompt,
    LeadCaptureRequest,
    LeadCaptureResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SourceChunk,
    ToolCall,
)
from .pipeline import RAGPipeline

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Global pipeline instance
pipeline: RAGPipeline | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup."""
    global pipeline

    logger.info("api_startup_begin")

    try:
        pipeline = RAGPipeline(
            vector_db_path=settings.vector_db_path,
            collection_name=settings.collection_name,
            metadata_db_url=settings.metadata_db_url,
            openai_api_key=settings.openai_api_key,
            embedding_model=settings.embedding_model,
            chunk_max_tokens=settings.chunk_max_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
        )

        # Initialize metadata store schema
        await pipeline.metadata_store.initialize()

        logger.info("api_startup_complete")
    except Exception as e:
        logger.error("api_startup_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("api_shutdown")


# Middleware for request logging
@app.middleware("http")
async def logging_middleware(request, call_next):
    """Log all requests."""
    start_time = time.time()
    method = request.method
    path = request.url.path

    logger.info("request_start", method=method, path=path)

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "request_complete",
            method=method,
            path=path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        logger.error(
            "request_error",
            method=method,
            path=path,
            duration_ms=duration_ms,
            error=str(e),
        )

        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)},
        )


@app.get("/")
async def root() -> Dict[str, Any]:
    """API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check for all components."""
    if pipeline is None:
        return HealthResponse(
            status="unhealthy",
            components={
                "pipeline": {
                    "healthy": False,
                    "message": "Pipeline not initialized",
                }
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    try:
        health_data = pipeline.health_check()

        # Convert to response format
        components = {}
        for name, data in health_data.items():
            if name == "status":
                continue

            components[name] = {
                "healthy": data.get("healthy", False),
                "message": data.get("error") or "OK",
                "latency_ms": data.get("latency_ms"),
            }

        return HealthResponse(
            status=health_data.get("status", "unknown"),
            components=components,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            components={"error": {"healthy": False, "message": str(e)}},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@app.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get pipeline statistics."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        return pipeline.get_stats()
    except Exception as e:
        logger.error("get_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
    user_id: str = Form(default="anonymous"),
) -> DocumentIngestResponse:
    """Ingest a document into the RAG system.

    Processes the document through the complete pipeline:
    1. Extract text from file
    2. Chunk into smaller pieces
    3. Generate embeddings
    4. Store in vector database

    Args:
        file: File to upload (TXT, PDF, DOCX)
        metadata: Optional JSON metadata for the document
        user_id: User identifier (defaults to "anonymous")

    Returns:
        DocumentIngestResponse with processing results
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Read file content
        content = await file.read()

        # Encode to base64
        import base64

        content_b64 = base64.b64encode(content).decode("utf-8")

        # Parse metadata
        import json

        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_dict = {}

        # Ingest document
        result = await pipeline.ingest_document(
            file.filename or "unknown",
            content_b64,
            user_id=user_id,
            metadata=metadata_dict,
        )

        return DocumentIngestResponse(**result)

    except ValueError as e:
        logger.warning("ingest_validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("ingest_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest) -> SearchResponse:
    """Search for similar documents.

    Uses semantic similarity to find relevant document chunks.

    Args:
        request: Search request with query and parameters

    Returns:
        SearchResponse with matching results
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    start_time = time.time()

    try:
        # Perform search
        results = pipeline.search(
            query=request.query,
            top_k=request.top_k,
            filter=request.filter,
            include_text=request.include_text,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        # Convert to response format
        result_items = [
            SearchResultItem(
                chunk_id=result.id,
                document_id=result.metadata.get("document_id", "unknown"),
                score=result.score,
                text=result.text if request.include_text else None,
                metadata=result.metadata,
            )
            for result in results
        ]

        return SearchResponse(
            query=request.query,
            results=result_items,
            total_results=len(result_items),
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error("search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/documents")
async def list_documents(
    user_id: str = "anonymous", limit: int = 100
) -> Dict[str, Any]:
    """List all documents for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of documents to return

    Returns:
        List of documents with metadata
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Get documents from metadata store (source of truth)
        documents = await pipeline.metadata_store.list_user_documents(
            user_id=user_id, limit=limit
        )

        return {
            "documents": [
                {
                    "id": doc.id,
                    "name": doc.name,
                    "user_id": doc.user_id,
                    "uploaded_at": doc.uploaded_at.isoformat(),
                    "status": doc.status,
                    "chunks_count": doc.chunks_count,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "metadata": doc.metadata_json,
                }
                for doc in documents
            ],
            "total": len(documents),
        }

    except Exception as e:
        logger.error("list_documents_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> Dict[str, Any]:
    """Delete a document and all its chunks.

    Args:
        document_id: Document identifier

    Returns:
        Deletion status
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Get chunk IDs from metadata store
        chunk_ids = await pipeline.metadata_store.delete_document(document_id)

        # Delete from vectorstore
        if chunk_ids:
            pipeline.vector_store.delete(chunk_ids)

        return {
            "document_id": document_id,
            "chunks_deleted": len(chunk_ids),
            "status": "deleted",
        }

    except Exception as e:
        logger.error("delete_document_error", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat with RAG system with OpenAI function calling and lead detection.

    Uses semantic search to find relevant context, then generates an answer
    using an LLM. Maintains conversation history across sessions.
    Supports tool calling for scheduling, contact, and portfolio links.
    Automatically detects lead signals and triggers lead capture when appropriate.

    Args:
        request: Chat request with message and parameters

    Returns:
        ChatResponse with answer, sources, tool_calls, and lead_capture
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Chat with pipeline
        result = await pipeline.chat(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            top_k=request.top_k,
            model=request.model,
            system_prompt=request.system_prompt,
        )

        # Convert to response format
        sources = [
            SourceChunk(
                chunk_id=s["chunk_id"],
                score=s["score"],
                text=s.get("text") if request.include_sources else None,
            )
            for s in result["sources"]
        ]

        # Convert tool calls
        tool_calls = [ToolCall(**tc) for tc in result.get("tool_calls", [])]

        # Convert lead capture
        lead_capture = None
        if result.get("lead_capture"):
            lead_capture = LeadCapturePrompt(**result["lead_capture"])

        return ChatResponse(
            answer=result["answer"],
            session_id=result["session_id"],
            sources=sources,
            model=result["model"],
            tokens_used=result["tokens_used"],
            cost_usd=result["cost_usd"],
            processing_time_ms=result["processing_time_ms"],
            tool_calls=tool_calls,
            lead_capture=lead_capture,
        )

    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/leads/capture", response_model=LeadCaptureResponse)
async def capture_lead(request: LeadCaptureRequest) -> LeadCaptureResponse:
    """Capture a lead from a conversation.

    Args:
        request: Lead capture request with session and contact information

    Returns:
        LeadCaptureResponse with lead ID
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Create lead in metadata store
        lead = await pipeline.metadata_store.create_lead(
            session_id=request.session_id,
            email=request.email,
            name=request.name,
            company=request.company,
            role=request.role,
            interest_level=request.interest_level,
            metadata={"source": "widget_capture"},
        )

        logger.info(
            "lead_captured",
            lead_id=lead.id,
            session_id=request.session_id,
            interest_level=request.interest_level,
        )

        return LeadCaptureResponse(
            lead_id=lead.id,
            session_id=request.session_id,
            message="Thank you for your interest! I'll be in touch soon.",
        )

    except Exception as e:
        logger.error("lead_capture_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# Admin Endpoints
@app.get("/admin/conversations")
async def list_conversations(
    page: int = 1,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List all conversations (admin only).

    Args:
        page: Page number (1-based)
        limit: Results per page
        user_id: Optional filter by user_id

    Returns:
        List of conversations with metadata
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        offset = (page - 1) * limit

        # Get sessions (optionally filtered by user_id)
        if user_id:
            sessions = await pipeline.metadata_store.list_user_sessions(
                user_id=user_id, limit=limit, offset=offset
            )
        else:
            # For admin, we'd need a list_all_sessions method
            # For now, use a placeholder user query
            sessions = []

        conversations = []
        for session in sessions:
            # Get message count and last message
            messages = await pipeline.metadata_store.get_conversation_history(
                session.id, limit=1
            )
            last_message = messages[0] if messages else None

            conversations.append(
                {
                    "session_id": session.id,
                    "user_id": session.user_id,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "message_count": session.message_count,
                    "last_message_preview": (
                        last_message.content[:100] + "..."
                        if last_message and len(last_message.content) > 100
                        else last_message.content if last_message else None
                    ),
                }
            )

        return {
            "conversations": conversations,
            "page": page,
            "limit": limit,
            "total": len(conversations),
        }

    except Exception as e:
        logger.error("list_conversations_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/conversations/{session_id}")
async def get_conversation(session_id: str) -> Dict[str, Any]:
    """Get full conversation by session ID (admin only).

    Args:
        session_id: Session identifier

    Returns:
        Full conversation with all messages
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Get session
        session = await pipeline.metadata_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get all messages
        messages = await pipeline.metadata_store.get_conversation_history(
            session_id, limit=1000
        )

        # Check for lead
        lead = await pipeline.metadata_store.get_lead_by_session(session_id)

        return {
            "session": {
                "id": session.id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "message_count": session.message_count,
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "model": msg.model,
                    "tokens_used": msg.tokens_used,
                    "cost_usd": msg.cost_usd,
                    "sources": msg.sources_json,
                    "metadata": msg.metadata_json,
                }
                for msg in messages
            ],
            "lead": (
                {
                    "id": lead.id,
                    "email": lead.email,
                    "name": lead.name,
                    "company": lead.company,
                    "role": lead.role,
                    "interest_level": lead.interest_level,
                    "captured_at": lead.captured_at.isoformat(),
                }
                if lead
                else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_conversation_error", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/leads")
async def list_leads(
    page: int = 1,
    limit: int = 50,
    interest_level: Optional[str] = None,
) -> Dict[str, Any]:
    """List all leads (admin only).

    Args:
        page: Page number (1-based)
        limit: Results per page
        interest_level: Optional filter by interest level (low, medium, high)

    Returns:
        List of leads with metadata
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        offset = (page - 1) * limit

        # Get leads
        leads = await pipeline.metadata_store.list_leads(
            limit=limit,
            offset=offset,
            interest_level=interest_level,
        )

        return {
            "leads": [
                {
                    "id": lead.id,
                    "session_id": lead.session_id,
                    "email": lead.email,
                    "name": lead.name,
                    "company": lead.company,
                    "role": lead.role,
                    "interest_level": lead.interest_level,
                    "captured_at": lead.captured_at.isoformat(),
                    "metadata": lead.metadata_json,
                }
                for lead in leads
            ],
            "page": page,
            "limit": limit,
            "total": len(leads),
        }

    except Exception as e:
        logger.error("list_leads_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/admin/analytics")
async def get_analytics() -> Dict[str, Any]:
    """Get analytics dashboard data (admin only).

    Returns:
        Analytics metrics including lead stats and conversation stats
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        # Get lead stats
        lead_stats = await pipeline.metadata_store.get_lead_stats()

        # Get pipeline stats
        pipeline_stats = pipeline.get_stats()

        return {
            "leads": lead_stats,
            "pipeline": pipeline_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error("get_analytics_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
