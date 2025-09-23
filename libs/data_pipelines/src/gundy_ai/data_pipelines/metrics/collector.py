"""Metrics collection for data pipelines processing."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for a processing operation."""

    # Timing metrics
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_time_ms: float = 0.0

    # Document metrics
    document_count: int = 0
    total_text_length: int = 0
    total_word_count: int = 0
    total_chunk_count: int = 0

    # Processing details
    parser_used: Optional[str] = None
    chunking_strategy: Optional[str] = None
    text_cleaning_enabled: bool = False
    ocr_used: bool = False

    # Quality metrics
    success_rate: float = 1.0
    error_count: int = 0
    retry_count: int = 0

    # Performance metrics
    throughput_docs_per_second: float = 0.0
    throughput_chars_per_second: float = 0.0
    memory_usage_mb: float = 0.0

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from base metrics."""
        if self.end_time and self.start_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()

            if duration_seconds > 0:
                self.throughput_docs_per_second = self.document_count / duration_seconds
                self.throughput_chars_per_second = (
                    self.total_text_length / duration_seconds
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time_ms": self.processing_time_ms,
            "document_count": self.document_count,
            "total_text_length": self.total_text_length,
            "total_word_count": self.total_word_count,
            "total_chunk_count": self.total_chunk_count,
            "parser_used": self.parser_used,
            "chunking_strategy": self.chunking_strategy,
            "text_cleaning_enabled": self.text_cleaning_enabled,
            "ocr_used": self.ocr_used,
            "success_rate": self.success_rate,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "throughput_docs_per_second": self.throughput_docs_per_second,
            "throughput_chars_per_second": self.throughput_chars_per_second,
            "memory_usage_mb": self.memory_usage_mb,
            "metadata": self.metadata,
        }


class MetricsCollector:
    """Collector for processing metrics and statistics."""

    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics entries to keep in memory
        """
        self.max_history = max_history
        self.metrics_history: deque[ProcessingMetrics] = deque(maxlen=max_history)
        self.current_metrics: Dict[str, ProcessingMetrics] = {}

        # Aggregated statistics
        self.total_documents_processed = 0
        self.total_processing_time_ms = 0.0
        self.total_errors = 0
        self.total_retries = 0

        # Performance tracking
        self.parser_usage_counts = defaultdict(int)
        self.chunking_strategy_counts = defaultdict(int)
        self.error_types = defaultdict(int)

        # Time-based metrics
        self.hourly_stats = defaultdict(
            lambda: {"documents": 0, "processing_time_ms": 0.0, "errors": 0}
        )

        self.logger = logger.bind(component="metrics_collector")

    def start_processing(self, operation_id: str, **metadata: Any) -> ProcessingMetrics:
        """Start tracking metrics for a processing operation.

        Args:
            operation_id: Unique identifier for the operation
            **metadata: Additional metadata to track

        Returns:
            ProcessingMetrics instance for this operation
        """
        metrics = ProcessingMetrics(start_time=datetime.utcnow(), metadata=metadata)

        self.current_metrics[operation_id] = metrics

        self.logger.debug("metrics_tracking_started", operation_id=operation_id)
        return metrics

    def update_processing_metrics(
        self, operation_id: str, **updates: Any
    ) -> Optional[ProcessingMetrics]:
        """Update metrics for an ongoing operation.

        Args:
            operation_id: Operation identifier
            **updates: Metric updates to apply

        Returns:
            Updated ProcessingMetrics or None if operation not found
        """
        if operation_id not in self.current_metrics:
            self.logger.warning(
                "metrics_operation_not_found", operation_id=operation_id
            )
            return None

        metrics = self.current_metrics[operation_id]

        # Update metrics fields
        for key, value in updates.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        return metrics

    def finish_processing(
        self,
        operation_id: str,
        success: bool = True,
        error_type: Optional[str] = None,
        **final_updates: Any,
    ) -> Optional[ProcessingMetrics]:
        """Finish tracking metrics for a processing operation.

        Args:
            operation_id: Operation identifier
            success: Whether the operation was successful
            error_type: Type of error if operation failed
            **final_updates: Final metric updates

        Returns:
            Final ProcessingMetrics or None if operation not found
        """
        if operation_id not in self.current_metrics:
            self.logger.warning(
                "metrics_operation_not_found", operation_id=operation_id
            )
            return None

        metrics = self.current_metrics[operation_id]

        # Set end time and calculate duration
        metrics.end_time = datetime.utcnow()
        if metrics.start_time:
            duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.processing_time_ms = duration * 1000

        # Apply final updates
        for key, value in final_updates.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        # Update success/error metrics
        if not success:
            metrics.error_count += 1
            metrics.success_rate = 0.0
            if error_type:
                self.error_types[error_type] += 1

        # Calculate derived metrics
        metrics.calculate_derived_metrics()

        # Update aggregated statistics
        self._update_aggregated_stats(metrics)

        # Add to history
        self.metrics_history.append(metrics)

        # Remove from current tracking
        del self.current_metrics[operation_id]

        self.logger.info(
            "metrics_tracking_finished",
            operation_id=operation_id,
            success=success,
            processing_time_ms=metrics.processing_time_ms,
            document_count=metrics.document_count,
        )

        return metrics

    def record_parser_usage(self, parser_name: str) -> None:
        """Record usage of a parser."""
        self.parser_usage_counts[parser_name] += 1

    def record_chunking_strategy(self, strategy_name: str) -> None:
        """Record usage of a chunking strategy."""
        self.chunking_strategy_counts[strategy_name] += 1

    def record_error(self, error_type: str, operation_id: Optional[str] = None) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type/category of the error
            operation_id: Optional operation identifier
        """
        self.error_types[error_type] += 1
        self.total_errors += 1

        if operation_id and operation_id in self.current_metrics:
            self.current_metrics[operation_id].error_count += 1

    def record_retry(self, operation_id: Optional[str] = None) -> None:
        """Record a retry attempt.

        Args:
            operation_id: Optional operation identifier
        """
        self.total_retries += 1

        if operation_id and operation_id in self.current_metrics:
            self.current_metrics[operation_id].retry_count += 1

    def get_current_metrics(self) -> Dict[str, ProcessingMetrics]:
        """Get currently tracked metrics."""
        return self.current_metrics.copy()

    def get_recent_metrics(self, count: int = 10) -> List[ProcessingMetrics]:
        """Get recent completed metrics.

        Args:
            count: Number of recent metrics to return

        Returns:
            List of recent ProcessingMetrics
        """
        return list(self.metrics_history)[-count:]

    def get_metrics_in_timerange(
        self, start_time: datetime, end_time: datetime
    ) -> List[ProcessingMetrics]:
        """Get metrics within a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of ProcessingMetrics in the time range
        """
        return [
            metrics
            for metrics in self.metrics_history
            if metrics.start_time >= start_time
            and (metrics.end_time or datetime.utcnow()) <= end_time
        ]

    def get_aggregated_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        total_operations = len(self.metrics_history)

        if total_operations == 0:
            return {
                "total_operations": 0,
                "total_documents": 0,
                "total_processing_time_ms": 0.0,
                "average_processing_time_ms": 0.0,
                "total_errors": 0,
                "error_rate": 0.0,
                "total_retries": 0,
                "parser_usage": {},
                "chunking_strategy_usage": {},
                "error_breakdown": {},
            }

        # Calculate averages
        avg_processing_time = self.total_processing_time_ms / total_operations
        error_rate = self.total_errors / total_operations

        # Get recent performance metrics
        recent_metrics = self.get_recent_metrics(100)
        recent_throughput_docs = [
            m.throughput_docs_per_second
            for m in recent_metrics
            if m.throughput_docs_per_second > 0
        ]
        recent_throughput_chars = [
            m.throughput_chars_per_second
            for m in recent_metrics
            if m.throughput_chars_per_second > 0
        ]

        avg_throughput_docs = (
            sum(recent_throughput_docs) / len(recent_throughput_docs)
            if recent_throughput_docs
            else 0.0
        )
        avg_throughput_chars = (
            sum(recent_throughput_chars) / len(recent_throughput_chars)
            if recent_throughput_chars
            else 0.0
        )

        return {
            "total_operations": total_operations,
            "total_documents": self.total_documents_processed,
            "total_processing_time_ms": self.total_processing_time_ms,
            "average_processing_time_ms": avg_processing_time,
            "total_errors": self.total_errors,
            "error_rate": error_rate,
            "total_retries": self.total_retries,
            "average_throughput_docs_per_second": avg_throughput_docs,
            "average_throughput_chars_per_second": avg_throughput_chars,
            "parser_usage": dict(self.parser_usage_counts),
            "chunking_strategy_usage": dict(self.chunking_strategy_counts),
            "error_breakdown": dict(self.error_types),
            "hourly_stats": dict(self.hourly_stats),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the last period."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)

        recent_hour = self.get_metrics_in_timerange(last_hour, now)
        recent_day = self.get_metrics_in_timerange(last_day, now)

        def calculate_stats(metrics_list: List[ProcessingMetrics]) -> Dict[str, Any]:
            if not metrics_list:
                return {
                    "operations": 0,
                    "documents": 0,
                    "avg_processing_time_ms": 0.0,
                    "success_rate": 1.0,
                    "throughput_docs_per_second": 0.0,
                }

            total_docs = sum(m.document_count for m in metrics_list)
            total_time = sum(m.processing_time_ms for m in metrics_list)
            successful_ops = sum(1 for m in metrics_list if m.error_count == 0)

            throughputs = [
                m.throughput_docs_per_second
                for m in metrics_list
                if m.throughput_docs_per_second > 0
            ]
            avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0.0

            return {
                "operations": len(metrics_list),
                "documents": total_docs,
                "avg_processing_time_ms": total_time / len(metrics_list),
                "success_rate": successful_ops / len(metrics_list),
                "throughput_docs_per_second": avg_throughput,
            }

        return {
            "last_hour": calculate_stats(recent_hour),
            "last_day": calculate_stats(recent_day),
            "all_time": self.get_aggregated_stats(),
        }

    def _update_aggregated_stats(self, metrics: ProcessingMetrics) -> None:
        """Update aggregated statistics with new metrics."""
        self.total_documents_processed += metrics.document_count
        self.total_processing_time_ms += metrics.processing_time_ms

        if metrics.parser_used:
            self.parser_usage_counts[metrics.parser_used] += 1

        if metrics.chunking_strategy:
            self.chunking_strategy_counts[metrics.chunking_strategy] += 1

        # Update hourly stats
        if metrics.start_time:
            hour_key = metrics.start_time.strftime("%Y-%m-%d-%H")
            self.hourly_stats[hour_key]["documents"] += metrics.document_count
            self.hourly_stats[hour_key][
                "processing_time_ms"
            ] += metrics.processing_time_ms
            self.hourly_stats[hour_key]["errors"] += metrics.error_count

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self.metrics_history.clear()
        self.current_metrics.clear()

        self.total_documents_processed = 0
        self.total_processing_time_ms = 0.0
        self.total_errors = 0
        self.total_retries = 0

        self.parser_usage_counts.clear()
        self.chunking_strategy_counts.clear()
        self.error_types.clear()
        self.hourly_stats.clear()

        self.logger.info("metrics_reset")
