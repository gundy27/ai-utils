"""RAG pipeline integration."""

import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from gundy_ai.chunker import TokenAwareChunker
from gundy_ai.embeddings import OpenAIEmbeddingProvider
from gundy_ai.extractors import ParserRegistry, PDFParser, TXTParser
from gundy_ai.llm import OpenAIClient
from gundy_ai.metadata_store import MetadataStore
from gundy_ai.vectorstore import ChromaDBAdapter, QueryResult

from .lead_detection import detect_interest_signal
from .tools import CALENDLY_TOOL, CONTACT_TOOL, PORTFOLIO_TOOL, ToolRegistry

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """Complete RAG pipeline: extract → chunk → embed → store.

    Integrates all gundy-ai libraries into a cohesive pipeline.
    """

    def __init__(
        self,
        vector_db_path: str = "./vector_db",
        collection_name: str = "documents",
        metadata_db_url: str = "sqlite+aiosqlite:///./metadata.db",
        openai_api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        chunk_max_tokens: int = 512,
        chunk_overlap_tokens: int = 50,
    ):
        """Initialize RAG pipeline.

        Args:
            vector_db_path: Path to vector database
            collection_name: Collection name for vectors
            metadata_db_url: Metadata store database URL
            openai_api_key: OpenAI API key (or use OPENAI_API_KEY env var)
            embedding_model: Embedding model to use
            chunk_max_tokens: Maximum tokens per chunk
            chunk_overlap_tokens: Overlap between chunks
        """
        logger.info(
            "rag_pipeline_init",
            vector_db_path=vector_db_path,
            collection=collection_name,
            embedding_model=embedding_model,
        )

        # Initialize parser registry
        self.parser_registry = ParserRegistry()
        self.parser_registry.register(TXTParser())
        self.parser_registry.register(PDFParser())

        # Try to register DOCX parser if available
        try:
            from gundy_ai.extractors import DOCXParser

            self.parser_registry.register(DOCXParser())
        except ImportError:
            logger.warning(
                "docx_parser_unavailable", reason="python-docx not installed"
            )

        # Initialize chunker
        self.chunker = TokenAwareChunker(
            max_tokens=chunk_max_tokens, overlap_tokens=chunk_overlap_tokens
        )

        # Initialize embedding provider
        self.embeddings = OpenAIEmbeddingProvider(
            api_key=openai_api_key, model=embedding_model
        )

        # Initialize vector store
        self.vector_store = ChromaDBAdapter(
            persist_directory=vector_db_path, collection_name=collection_name
        )

        # Initialize metadata store
        self.metadata_store = MetadataStore(metadata_db_url)

        # Initialize LLM client (set env var for OpenAIClient)
        import os

        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        self.llm = OpenAIClient()

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(CALENDLY_TOOL)
        self.tool_registry.register(CONTACT_TOOL)
        self.tool_registry.register(PORTFOLIO_TOOL)

        logger.info("rag_pipeline_initialized")

    async def ingest_document(
        self,
        file_name: str,
        file_content_base64: str,
        user_id: str = "anonymous",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingest a document through the complete pipeline.

        Args:
            file_name: Name of the file
            file_content_base64: Base64 encoded file content
            user_id: User identifier
            metadata: Optional document metadata

        Returns:
            Dictionary with ingestion results

        Raises:
            ValueError: If file type not supported
            RuntimeError: If processing fails
        """
        start_time = time.time()

        # Get file extension
        file_ext = Path(file_name).suffix.lower()
        if not file_ext:
            raise ValueError(f"File must have an extension: {file_name}")

        # Get parser for file type
        parser = self.parser_registry.get_parser(file_ext)
        if not parser:
            supported = self.parser_registry.list_supported_types()
            raise ValueError(
                f"Unsupported file type: {file_ext}. Supported: {supported}"
            )

        logger.info("document_ingest_start", file_name=file_name, file_type=file_ext)

        # Decode file content and save to temp file
        try:
            file_bytes = base64.b64decode(file_content_base64)
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}") from e

        # Create unique document ID
        import uuid

        document_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Process file
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        try:
            # Step 1: Extract text
            extracted_chunks = parser.parse(tmp_path)
            logger.info("extraction_complete", chunks=len(extracted_chunks))

            # Step 2: Chunk the text
            all_chunks = []
            for extracted in extracted_chunks:
                chunks = self.chunker.chunk(extracted.text)
                all_chunks.extend(chunks)

            logger.info("chunking_complete", chunks=len(all_chunks))

            # Step 3: Generate embeddings
            chunk_texts = [chunk.text for chunk in all_chunks]
            embedding_result = self.embeddings.embed(chunk_texts)

            logger.info(
                "embedding_complete",
                embeddings=len(embedding_result.embeddings),
                tokens=embedding_result.total_tokens,
                cost=embedding_result.estimated_cost_usd,
            )

            # Step 4: Store in vector database
            chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(all_chunks))]
            chunk_metadatas = [
                {
                    "document_id": document_id,
                    "document_name": file_name,
                    "chunk_index": i,
                    "token_count": chunk.token_count,
                    "user_id": user_id,
                    **(metadata or {}),
                }
                for i, chunk in enumerate(all_chunks)
            ]

            self.vector_store.upsert(
                ids=chunk_ids,
                embeddings=embedding_result.embeddings,
                metadatas=chunk_metadatas,
                texts=chunk_texts,
            )

            logger.info("vectorstore_complete", vectors=len(chunk_ids))

            # Track in metadata store
            await self.metadata_store.create_document(
                name=file_name,
                user_id=user_id,
                chunks=chunk_ids,
                status="completed",
                file_size=len(file_bytes),
                file_type=file_ext,
                metadata=metadata,
            )

            logger.info("metadata_store_complete", document_id=document_id)

            processing_time_ms = (time.time() - start_time) * 1000

            result = {
                "document_id": document_id,
                "chunks_created": len(all_chunks),
                "vectors_stored": len(chunk_ids),
                "total_tokens": embedding_result.total_tokens,
                "estimated_cost_usd": embedding_result.estimated_cost_usd,
                "processing_time_ms": processing_time_ms,
            }

            logger.info("document_ingest_complete", **result)

            return result

        finally:
            # Cleanup temp file
            Path(tmp_path).unlink(missing_ok=True)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_text: bool = True,
    ) -> List[QueryResult]:
        """Search for similar documents.

        Args:
            query: Search query
            top_k: Number of results to return
            filter: Optional metadata filter
            include_text: Include text in results

        Returns:
            List of QueryResult objects
        """
        start_time = time.time()

        logger.info("search_start", query_length=len(query), top_k=top_k)

        # Generate query embedding
        query_embedding_result = self.embeddings.embed([query])
        query_embedding = query_embedding_result.embeddings[0]

        logger.info(
            "query_embedding_complete",
            dimensions=len(query_embedding),
            tokens=query_embedding_result.total_tokens,
        )

        # Search vector store
        results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filter,
            include_embeddings=False,
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "search_complete",
            results_found=len(results),
            processing_time_ms=processing_time_ms,
        )

        return results

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document identifier

        Returns:
            Number of chunks deleted
        """
        logger.info("document_delete_start", document_id=document_id)

        # Query for all chunks with this document_id
        # ChromaDB doesn't have a built-in way to get all IDs by metadata,
        # so we'll search with a dummy embedding and filter
        # This is a workaround - in production you'd track document->chunk mappings

        # For now, we'll use a simple pattern match on chunk IDs
        # In production, maintain a separate document->chunks index

        # Since ChromaDB doesn't support pattern matching in delete,
        # we need to track chunks differently or query first

        # Simplified approach: assume chunk IDs follow pattern {document_id}_chunk_*
        # Get all chunks and filter (not ideal for large collections)

        # Better approach: use metadata filter to find chunks
        try:
            # This is a limitation - we'll need to enhance this
            # For now, return 0 and log warning
            logger.warning(
                "document_delete_not_implemented",
                document_id=document_id,
                reason="Need metadata-based bulk delete",
            )
            return 0
        except Exception as e:
            logger.error(
                "document_delete_failed", document_id=document_id, error=str(e)
            )
            raise

    def health_check(self) -> Dict[str, Any]:
        """Check health of all pipeline components.

        Returns:
            Dictionary with health status of each component
        """
        health = {}

        # Check vector store
        try:
            vs_health = self.vector_store.health_check()
            health["vector_store"] = {
                "healthy": vs_health["healthy"],
                "count": vs_health.get("count"),
                "latency_ms": vs_health.get("latency_ms"),
            }
        except Exception as e:
            health["vector_store"] = {"healthy": False, "error": str(e)}

        # Check embedding provider
        try:
            emb_health = self.embeddings.health_check()
            health["embeddings"] = {
                "healthy": emb_health["healthy"],
                "model": emb_health.get("model"),
                "latency_ms": emb_health.get("latency_ms"),
            }
        except Exception as e:
            health["embeddings"] = {"healthy": False, "error": str(e)}

        # Check parsers
        health["parsers"] = {
            "healthy": True,
            "registered": len(self.parser_registry.list_parsers()),
            "supported_types": self.parser_registry.get_supported_extensions(),
        }

        # Check chunker
        health["chunker"] = {
            "healthy": True,
            "max_tokens": self.chunker.max_tokens,
            "overlap_tokens": self.chunker.overlap_tokens,
        }

        # Overall status
        all_healthy = all(
            comp.get("healthy", False)
            for comp in [health["vector_store"], health["embeddings"]]
        )
        health["status"] = "healthy" if all_healthy else "unhealthy"

        return health

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: str = "anonymous",
        top_k: int = 5,
        model: str = "gpt-4o-mini",
        include_history: bool = True,
        system_prompt: Optional[str] = None,
        enable_tools: bool = True,
        enable_lead_detection: bool = True,
    ) -> Dict[str, Any]:
        """Chat with RAG system with OpenAI function calling and lead detection.

        Args:
            message: User message
            session_id: Optional session ID for conversation history
            user_id: User identifier
            top_k: Number of context chunks to retrieve
            model: LLM model to use
            include_history: Include conversation history in context
            system_prompt: Custom system prompt
            enable_tools: Enable OpenAI function calling for tools
            enable_lead_detection: Enable automatic lead signal detection

        Returns:
            Dictionary with answer, sources, tool_calls, lead_capture, and metadata
        """
        start_time = time.time()

        # Get or create session
        if session_id:
            session = await self.metadata_store.get_session(session_id)
            if not session:
                session = await self.metadata_store.create_session(user_id=user_id)
        else:
            session = await self.metadata_store.create_session(user_id=user_id)

        logger.info("chat_start", session_id=session.id, user_id=user_id)

        # Save user message
        await self.metadata_store.add_message(
            session_id=session.id, role="user", content=message
        )

        # Search for relevant context - filter by user_id for RBAC
        search_results = self.search(
            query=message, top_k=top_k, filter={"user_id": user_id}, include_text=True
        )

        # Build context from search results
        context_parts = [
            f"[Source {i+1}]: {r.text}" for i, r in enumerate(search_results)
        ]
        context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No relevant documents found."
        )

        # Get conversation history if requested
        history_messages = []
        if include_history and session.message_count > 0:
            history = await self.metadata_store.get_conversation_history(
                session.id,
                limit=6,  # Last 3 exchanges
            )
            # Exclude the message we just added
            history_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in history[:-1]  # Exclude last (current user message)
            ]

        # Construct LLM prompt
        # Use custom system prompt if provided, otherwise use default
        system_message = system_prompt or (
            "You are a helpful assistant representing Dan Gunderson, a software engineer. "
            "Answer questions based on the provided context about Dan's experience, skills, and projects. "
            "If the context doesn't contain relevant information, say so clearly. "
            "Be professional, concise, and helpful. When appropriate, use available tools to help the user."
        )

        messages = [{"role": "system", "content": system_message}]

        # Add history
        messages.extend(history_messages)

        # Add context and current question
        user_prompt = f"Context from documents:\n\n{context}\n\nQuestion: {message}"
        messages.append({"role": "user", "content": user_prompt})

        # Prepare OpenAI function calling with tools
        extra_params = {}
        if enable_tools:
            tool_schemas = self.tool_registry.get_tool_schemas()
            if tool_schemas:
                extra_params["tools"] = tool_schemas
                extra_params["tool_choice"] = "auto"

        # Call LLM with tools
        # Note: OpenAI's chat method returns string, but with tools we need the full response
        # We'll need to use the underlying client directly for tool calls
        from openai import OpenAI

        openai_client = OpenAI(api_key=self.llm.api_key)

        response = openai_client.chat.completions.create(
            model=model, messages=messages, max_tokens=500, **extra_params
        )

        # Extract answer and tool calls
        answer = ""
        tool_calls_data = []

        if response.choices:
            choice = response.choices[0]
            message_obj = choice.message

            # Get text content
            if message_obj.content:
                answer = message_obj.content

            # Get tool calls
            if message_obj.tool_calls:
                for tool_call in message_obj.tool_calls:
                    try:
                        # Parse arguments
                        args = json.loads(tool_call.function.arguments)

                        # Execute tool
                        result = self.tool_registry.execute(
                            tool_call.function.name, args
                        )

                        # Add tool name to result for Pydantic validation
                        result["tool"] = tool_call.function.name

                        tool_calls_data.append(result)

                    except Exception as e:
                        logger.error(
                            "tool_execution_failed",
                            tool_name=tool_call.function.name,
                            error=str(e),
                        )

        # Estimate tokens (rough approximation)
        total_tokens = len(message.split()) + len(answer.split()) + len(context.split())
        estimated_tokens = int(total_tokens * 1.3)

        # Estimate cost (for gpt-4o-mini: $0.15/1M input, $0.60/1M output)
        input_cost = (estimated_tokens * 0.15) / 1_000_000
        output_cost = (len(answer.split()) * 1.3 * 0.60) / 1_000_000
        estimated_cost = input_cost + output_cost

        # Detect lead signals
        lead_capture_data = None
        if enable_lead_detection:
            # Get all conversation history for lead detection
            all_history = await self.metadata_store.get_conversation_history(
                session.id, limit=100
            )

            conversation_for_detection = [
                {"role": msg.role, "content": msg.content} for msg in all_history
            ]

            context_used = [r.text or "" for r in search_results]

            signal = detect_interest_signal(
                message=message,
                conversation_history=conversation_for_detection,
                context_used=context_used,
            )

            if signal["should_capture"]:
                lead_capture_data = {
                    "should_capture": True,
                    "interest_level": signal["interest_level"],
                    "trigger": signal["trigger"],
                    "message": "I'd love to learn more about your interest! Would you mind sharing your contact information?",
                }

                logger.info(
                    "lead_capture_triggered",
                    session_id=session.id,
                    interest_level=signal["interest_level"],
                    trigger=signal["trigger"],
                )

        # Save assistant message
        await self.metadata_store.add_message(
            session_id=session.id,
            role="assistant",
            content=answer,
            model=model,
            tokens_used=estimated_tokens,
            cost_usd=estimated_cost,
            sources={"chunks": [r.id for r in search_results]},
            metadata={
                "tool_calls": tool_calls_data,
                "lead_capture_triggered": lead_capture_data is not None,
            },
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "chat_complete",
            session_id=session.id,
            tokens=estimated_tokens,
            cost=estimated_cost,
            processing_time_ms=processing_time_ms,
            tools_called=len(tool_calls_data),
            lead_triggered=lead_capture_data is not None,
        )

        return {
            "answer": answer,
            "session_id": session.id,
            "sources": [
                {
                    "chunk_id": r.id,
                    "score": r.score,
                    "text": r.text if include_history else None,
                }
                for r in search_results
            ],
            "model": model,
            "tokens_used": estimated_tokens,
            "cost_usd": estimated_cost,
            "processing_time_ms": processing_time_ms,
            "tool_calls": tool_calls_data,
            "lead_capture": lead_capture_data,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics.

        Returns:
            Dictionary with pipeline stats
        """
        try:
            vector_count = self.vector_store.count()
        except Exception as e:
            logger.warning("vector_count_failed", error=str(e))
            vector_count = 0

        return {
            "vector_count": vector_count,
            "parsers_registered": len(self.parser_registry.list_parsers()),
            "supported_file_types": self.parser_registry.get_supported_extensions(),
            "chunk_max_tokens": self.chunker.max_tokens,
            "embedding_model": self.embeddings.model_name,
            "embedding_dimensions": self.embeddings.dimensions,
        }
