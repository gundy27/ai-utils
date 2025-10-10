"""Metadata and session management for RAG applications."""

from .audit import MetadataAuditEvent, MetadataEventType, emit_metadata_event
from .models import Base, Document, DocumentChunk, Message, Session
from .store import MetadataStore

__version__ = "0.1.0"

__all__ = [
    "MetadataStore",
    "Session",
    "Message",
    "Document",
    "DocumentChunk",
    "Base",
    "MetadataAuditEvent",
    "MetadataEventType",
    "emit_metadata_event",
]
