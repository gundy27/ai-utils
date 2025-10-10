"""SQLAlchemy models for metadata store."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Session(Base):
    """Chat session model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_activity: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __table_args__ = (
        Index("ix_sessions_user_last_activity", "user_id", "last_activity"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"


class Message(Base):
    """Chat message model."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )  # Foreign key in production
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sources_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "sources", JSON, nullable=True
    )  # Chunk references
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __table_args__ = (
        Index("ix_messages_session_timestamp", "session_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session={self.session_id}, role={self.role})>"


class Document(Base):
    """Document metadata model."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="processing", nullable=False
    )  # processing, completed, failed
    chunks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __table_args__ = (Index("ix_documents_user_uploaded", "user_id", "uploaded_at"),)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name={self.name}, status={self.status})>"


class DocumentChunk(Base):
    """Document-to-chunk mapping model."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    chunk_id: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )  # References vectorstore
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_doc_chunks_document", "document_id"),
        Index("ix_doc_chunks_chunk_id", "chunk_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(doc={self.document_id}, chunk={self.chunk_id})>"
