"""RAG API main application."""

import time
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .models import (
    DocumentIngestResponse,
    HealthResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
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
            openai_api_key=settings.openai_api_key,
            embedding_model=settings.embedding_model,
            chunk_max_tokens=settings.chunk_max_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
        )

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
    file: UploadFile = File(...), metadata: str = Form(default="{}")
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
        result = pipeline.ingest_document(
            file.filename or "unknown", content_b64, metadata_dict
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
async def list_documents() -> Dict[str, Any]:
    """List all documents.

    Note: This is a simplified implementation.
    In production, maintain a separate document index.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        stats = pipeline.get_stats()

        return {
            "message": "Document listing requires separate document index",
            "total_vectors": stats["vector_count"],
            "note": "Each document may have multiple vectors (chunks)",
        }

    except Exception as e:
        logger.error("list_documents_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> Dict[str, Any]:
    """Delete a document and all its chunks.

    Note: This is a simplified implementation.
    In production, maintain a document->chunks index.

    Args:
        document_id: Document identifier

    Returns:
        Deletion status
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        chunks_deleted = pipeline.delete_document(document_id)

        return {
            "document_id": document_id,
            "chunks_deleted": chunks_deleted,
            "note": "Full document deletion requires document->chunks index",
        }

    except Exception as e:
        logger.error("delete_document_error", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail=str(e)) from e
