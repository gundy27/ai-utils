"""Request and response models for RAG API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Document Ingestion Models
class DocumentIngestRequest(BaseModel):
    """Request to ingest a document."""

    file_name: str = Field(description="Name of the file")
    file_content: str = Field(description="Base64 encoded file content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional document metadata"
    )


class DocumentIngestResponse(BaseModel):
    """Response from document ingestion."""

    document_id: str = Field(description="Unique document identifier")
    chunks_created: int = Field(description="Number of text chunks created")
    vectors_stored: int = Field(description="Number of vectors stored")
    total_tokens: int = Field(description="Total tokens embedded")
    estimated_cost_usd: float = Field(description="Estimated cost in USD")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


# Search Models
class SearchRequest(BaseModel):
    """Request to search documents."""

    query: str = Field(description="Search query")
    top_k: int = Field(
        default=5, ge=1, le=50, description="Number of results to return"
    )
    filter: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata filter"
    )
    include_text: bool = Field(
        default=True, description="Include document text in results"
    )


class SearchResultItem(BaseModel):
    """A single search result."""

    chunk_id: str = Field(description="Chunk identifier")
    document_id: str = Field(description="Source document identifier")
    score: float = Field(description="Similarity score (higher = more similar)")
    text: Optional[str] = Field(default=None, description="Chunk text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class SearchResponse(BaseModel):
    """Response from search."""

    query: str = Field(description="Original query")
    results: List[SearchResultItem] = Field(description="Search results")
    total_results: int = Field(description="Number of results found")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


# Document Management Models
class DocumentListResponse(BaseModel):
    """Response with list of documents."""

    documents: List[Dict[str, Any]] = Field(description="List of documents")
    total_count: int = Field(description="Total document count")


class DocumentDeleteResponse(BaseModel):
    """Response from document deletion."""

    document_id: str = Field(description="Deleted document ID")
    chunks_deleted: int = Field(description="Number of chunks deleted")


# Health Check Models
class ComponentHealth(BaseModel):
    """Health status of a component."""

    healthy: bool = Field(description="Whether component is healthy")
    message: Optional[str] = Field(default=None, description="Status message")
    latency_ms: Optional[float] = Field(default=None, description="Response latency")


class HealthResponse(BaseModel):
    """Overall health status."""

    status: str = Field(description="Overall status: ok, degraded, or unhealthy")
    components: Dict[str, ComponentHealth] = Field(
        description="Health status of each component"
    )
    timestamp: str = Field(description="Health check timestamp")


# Chat Models
class ChatRequest(BaseModel):
    """Request to chat with RAG."""

    message: str = Field(description="User message")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for conversation history"
    )
    user_id: str = Field(default="anonymous", description="User identifier")
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of context chunks to retrieve"
    )
    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    include_sources: bool = Field(
        default=True, description="Include source chunks in response"
    )


class SourceChunk(BaseModel):
    """Source chunk referenced in answer."""

    chunk_id: str = Field(description="Chunk identifier")
    score: float = Field(description="Similarity score")
    text: Optional[str] = Field(default=None, description="Chunk text")


class ChatResponse(BaseModel):
    """Response from chat."""

    answer: str = Field(description="LLM generated answer")
    session_id: str = Field(description="Session identifier")
    sources: List[SourceChunk] = Field(
        default_factory=list, description="Source chunks used"
    )
    model: str = Field(description="Model used")
    tokens_used: int = Field(description="Total tokens used")
    cost_usd: float = Field(description="Estimated cost in USD")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
