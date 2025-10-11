"""Metadata store implementation."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import create_engine, delete, desc, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .audit import MetadataEventType, emit_metadata_event
from .models import Base, Document, DocumentChunk, Lead, Message, Session

logger = structlog.get_logger(__name__)


class MetadataStore:
    """Metadata and session management store.

    Provides CRUD operations for sessions, messages, documents, and document chunks.
    Supports both SQLite (dev) and Postgres (prod).

    Example:
        # Async usage
        store = MetadataStore("sqlite+aiosqlite:///./metadata.db")
        await store.initialize()

        session = await store.create_session(user_id="user123")
        await store.add_message(session.id, "user", "Hello!")

        # Sync usage
        store = MetadataStore("sqlite:///./metadata.db", async_mode=False)
        store.initialize_sync()

        session = store.create_session_sync(user_id="user123")
    """

    def __init__(self, database_url: str, async_mode: bool = True, echo: bool = False):
        """Initialize metadata store.

        Args:
            database_url: Database connection string
            async_mode: Use async engine (default: True)
            echo: Echo SQL queries (default: False)
        """
        self.database_url = database_url
        self.async_mode = async_mode
        self.echo = echo

        if async_mode:
            self.engine: AsyncEngine = create_async_engine(database_url, echo=echo)
            self.async_session_maker = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
        else:
            self.sync_engine = create_engine(database_url, echo=echo)
            self.sync_session_maker = sessionmaker(
                self.sync_engine, expire_on_commit=False
            )

        logger.info(
            "metadata_store_initialized",
            database_url=database_url.split("@")[-1],  # Redact credentials
            async_mode=async_mode,
        )

    async def initialize(self):
        """Initialize database schema (async)."""
        if not self.async_mode:
            raise RuntimeError("Store is in sync mode, use initialize_sync()")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("database_schema_initialized")

    def initialize_sync(self):
        """Initialize database schema (sync)."""
        if self.async_mode:
            raise RuntimeError("Store is in async mode, use initialize()")

        Base.metadata.create_all(self.sync_engine)
        logger.info("database_schema_initialized")

    # Session Operations (Async)

    async def create_session(
        self, user_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a new chat session.

        Args:
            user_id: User identifier
            metadata: Optional session metadata

        Returns:
            Created Session object
        """
        session_id = f"session_{uuid.uuid4().hex[:16]}"

        session = Session(
            id=session_id, user_id=user_id, message_count=0, metadata_json=metadata
        )

        async with self.async_session_maker() as db_session:
            db_session.add(session)
            await db_session.commit()
            await db_session.refresh(session)

        emit_metadata_event(
            event_type=MetadataEventType.SESSION_CREATED,
            operation="create_session",
            outcome="success",
            user_id=user_id,
            session_id=session_id,
        )

        logger.info("session_created", session_id=session_id, user_id=user_id)

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Session).where(Session.id == session_id)
            )
            session = result.scalar_one_or_none()

        if session:
            emit_metadata_event(
                event_type=MetadataEventType.SESSION_ACCESSED,
                operation="get_session",
                outcome="success",
                session_id=session_id,
                user_id=session.user_id,
            )

        return session

    async def list_user_sessions(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Session]:
        """List sessions for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            List of Session objects
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(desc(Session.last_activity))
                .limit(limit)
                .offset(offset)
            )
            sessions = result.scalars().all()

        return list(sessions)

    # Message Operations (Async)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        sources: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to a session.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            model: Model used (for assistant messages)
            tokens_used: Tokens used
            cost_usd: Cost in USD
            sources: Source chunks referenced
            metadata: Additional metadata

        Returns:
            Created Message object
        """
        message_id = f"msg_{uuid.uuid4().hex[:16]}"

        message = Message(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            sources_json=sources,
            metadata_json=metadata,
        )

        async with self.async_session_maker() as db_session:
            # Add message
            db_session.add(message)

            # Update session message count and last activity
            result = await db_session.execute(
                select(Session).where(Session.id == session_id)
            )
            session = result.scalar_one_or_none()

            if session:
                session.message_count += 1
                session.last_activity = datetime.utcnow()

            await db_session.commit()
            await db_session.refresh(message)

        emit_metadata_event(
            event_type=MetadataEventType.MESSAGE_ADDED,
            operation="add_message",
            outcome="success",
            session_id=session_id,
            metadata={"role": role, "tokens": tokens_used, "cost": cost_usd},
        )

        logger.info(
            "message_added",
            message_id=message_id,
            session_id=session_id,
            role=role,
            tokens=tokens_used,
        )

        return message

    async def get_conversation_history(
        self, session_id: str, limit: int = 50, offset: int = 0
    ) -> List[Message]:
        """Get conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages
            offset: Offset for pagination

        Returns:
            List of Message objects ordered by timestamp
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.timestamp)
                .limit(limit)
                .offset(offset)
            )
            messages = result.scalars().all()

        return list(messages)

    # Document Operations (Async)

    async def create_document(
        self,
        name: str,
        user_id: str,
        chunks: List[str],
        status: str = "completed",
        file_size: Optional[int] = None,
        file_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a document record with chunk mappings.

        Args:
            name: Document name
            user_id: User identifier
            chunks: List of chunk IDs from vectorstore
            status: Document status (processing, completed, failed)
            file_size: File size in bytes
            file_type: File type/extension
            metadata: Additional metadata

        Returns:
            Created Document object
        """
        document_id = f"doc_{uuid.uuid4().hex[:12]}"

        document = Document(
            id=document_id,
            name=name,
            user_id=user_id,
            status=status,
            chunks_count=len(chunks),
            file_size=file_size,
            file_type=file_type,
            metadata_json=metadata,
        )

        # Create chunk mappings
        chunk_records = [
            DocumentChunk(document_id=document_id, chunk_id=chunk_id, chunk_index=idx)
            for idx, chunk_id in enumerate(chunks)
        ]

        async with self.async_session_maker() as db_session:
            db_session.add(document)
            db_session.add_all(chunk_records)
            await db_session.commit()
            await db_session.refresh(document)

        emit_metadata_event(
            event_type=MetadataEventType.DOCUMENT_CREATED,
            operation="create_document",
            outcome="success",
            user_id=user_id,
            document_id=document_id,
            metadata={"chunks": len(chunks), "status": status},
        )

        logger.info(
            "document_created",
            document_id=document_id,
            user_id=user_id,
            chunks=len(chunks),
        )

        return document

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID.

        Args:
            document_id: Document identifier

        Returns:
            Document object or None if not found
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

        return document

    async def list_user_documents(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Document]:
        """List documents for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of documents
            offset: Offset for pagination

        Returns:
            List of Document objects ordered by upload time
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(desc(Document.uploaded_at))
                .limit(limit)
                .offset(offset)
            )
            documents = result.scalars().all()

        return list(documents)

    async def delete_document(self, document_id: str) -> List[str]:
        """Delete a document and return chunk IDs for vectorstore deletion.

        Args:
            document_id: Document identifier

        Returns:
            List of chunk IDs that should be deleted from vectorstore
        """
        async with self.async_session_maker() as db_session:
            # Get chunk IDs
            chunk_result = await db_session.execute(
                select(DocumentChunk.chunk_id).where(
                    DocumentChunk.document_id == document_id
                )
            )
            chunk_ids = [row[0] for row in chunk_result.all()]

            # Delete chunks
            await db_session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )

            # Delete document
            await db_session.execute(delete(Document).where(Document.id == document_id))

            await db_session.commit()

        emit_metadata_event(
            event_type=MetadataEventType.DOCUMENT_DELETED,
            operation="delete_document",
            outcome="success",
            document_id=document_id,
            metadata={"chunks_deleted": len(chunk_ids)},
        )

        logger.info(
            "document_deleted", document_id=document_id, chunks_deleted=len(chunk_ids)
        )

        return chunk_ids

    async def get_document_chunks(self, document_id: str) -> List[str]:
        """Get all chunk IDs for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunk IDs
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(DocumentChunk.chunk_id)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunk_ids = [row[0] for row in result.all()]

        return chunk_ids

    # Lead Operations (Async)

    async def create_lead(
        self,
        session_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None,
        role: Optional[str] = None,
        interest_level: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Lead:
        """Create a new lead capture record.

        Args:
            session_id: Session identifier
            email: Lead email address
            name: Lead name
            company: Company name
            role: Job role/title
            interest_level: Interest level (low, medium, high)
            metadata: Additional metadata (trigger reason, etc.)

        Returns:
            Created Lead object
        """
        lead_id = f"lead_{uuid.uuid4().hex[:16]}"

        lead = Lead(
            id=lead_id,
            session_id=session_id,
            email=email,
            name=name,
            company=company,
            role=role,
            interest_level=interest_level,
            metadata_json=metadata,
        )

        async with self.async_session_maker() as db_session:
            db_session.add(lead)
            await db_session.commit()
            await db_session.refresh(lead)

        emit_metadata_event(
            event_type=MetadataEventType.DOCUMENT_CREATED,  # Reuse or create LEAD_CREATED
            operation="create_lead",
            outcome="success",
            session_id=session_id,
            metadata={"interest_level": interest_level, "email": email},
        )

        logger.info(
            "lead_created",
            lead_id=lead_id,
            session_id=session_id,
            interest_level=interest_level,
        )

        return lead

    async def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID.

        Args:
            lead_id: Lead identifier

        Returns:
            Lead object or None if not found
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()

        return lead

    async def get_lead_by_session(self, session_id: str) -> Optional[Lead]:
        """Get lead by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Lead object or None if not found
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(
                select(Lead).where(Lead.session_id == session_id)
            )
            lead = result.scalar_one_or_none()

        return lead

    async def list_leads(
        self,
        limit: int = 50,
        offset: int = 0,
        interest_level: Optional[str] = None,
    ) -> List[Lead]:
        """List all leads with optional filtering.

        Args:
            limit: Maximum number of leads to return
            offset: Offset for pagination
            interest_level: Filter by interest level (low, medium, high)

        Returns:
            List of Lead objects ordered by capture time (newest first)
        """
        async with self.async_session_maker() as db_session:
            query = select(Lead)

            if interest_level:
                query = query.where(Lead.interest_level == interest_level)

            query = query.order_by(desc(Lead.captured_at)).limit(limit).offset(offset)

            result = await db_session.execute(query)
            leads = result.scalars().all()

        return list(leads)

    async def update_lead(
        self, lead_id: str, updates: Dict[str, Any]
    ) -> Optional[Lead]:
        """Update a lead record.

        Args:
            lead_id: Lead identifier
            updates: Dictionary of fields to update
                (name, email, company, role, interest_level, metadata_json)

        Returns:
            Updated Lead object or None if not found
        """
        async with self.async_session_maker() as db_session:
            result = await db_session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()

            if not lead:
                return None

            # Update allowed fields
            for field, value in updates.items():
                if hasattr(lead, field):
                    setattr(lead, field, value)

            await db_session.commit()
            await db_session.refresh(lead)

        logger.info("lead_updated", lead_id=lead_id, updates=list(updates.keys()))

        return lead

    # Statistics

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary with user statistics
        """
        async with self.async_session_maker() as db_session:
            # Count sessions
            session_result = await db_session.execute(
                select(Session).where(Session.user_id == user_id)
            )
            session_count = len(session_result.scalars().all())

            # Count documents
            doc_result = await db_session.execute(
                select(Document).where(Document.user_id == user_id)
            )
            document_count = len(doc_result.scalars().all())

            # Get total messages and cost
            # This would require joins in production for better performance
            sessions = await self.list_user_sessions(user_id, limit=1000)
            total_messages = sum(s.message_count for s in sessions)

        return {
            "user_id": user_id,
            "sessions": session_count,
            "documents": document_count,
            "total_messages": total_messages,
        }

    async def get_lead_stats(self) -> Dict[str, Any]:
        """Get lead statistics.

        Returns:
            Dictionary with lead statistics
        """
        async with self.async_session_maker() as db_session:
            # Total leads
            total_result = await db_session.execute(select(Lead))
            total_leads = len(total_result.scalars().all())

            # By interest level
            high_result = await db_session.execute(
                select(Lead).where(Lead.interest_level == "high")
            )
            high_count = len(high_result.scalars().all())

            medium_result = await db_session.execute(
                select(Lead).where(Lead.interest_level == "medium")
            )
            medium_count = len(medium_result.scalars().all())

            low_result = await db_session.execute(
                select(Lead).where(Lead.interest_level == "low")
            )
            low_count = len(low_result.scalars().all())

        return {
            "total": total_leads,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        }
