"""Metrics reporting and visualization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from .collector import MetricsCollector, ProcessingMetrics

logger = structlog.get_logger(__name__)


@dataclass
class MetricsReport:
    """Comprehensive metrics report."""

    report_id: str
    generated_at: datetime
    time_range_start: datetime
    time_range_end: datetime

    # Summary statistics
    total_operations: int = 0
    total_documents: int = 0
    total_processing_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    success_rate: float = 1.0
    error_rate: float = 0.0

    # Performance metrics
    average_throughput_docs_per_second: float = 0.0
    average_throughput_chars_per_second: float = 0.0
    peak_throughput_docs_per_second: float = 0.0
    peak_throughput_chars_per_second: float = 0.0

    # Usage statistics
    parser_usage: Dict[str, int] = field(default_factory=dict)
    chunking_strategy_usage: Dict[str, int] = field(default_factory=dict)

    # Error analysis
    error_breakdown: Dict[str, int] = field(default_factory=dict)
    total_errors: int = 0
    total_retries: int = 0

    # Time-based analysis
    hourly_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    daily_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Quality metrics
    ocr_usage_rate: float = 0.0
    text_cleaning_usage_rate: float = 0.0
    average_chunk_count_per_document: float = 0.0

    # Additional insights
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "time_range_start": self.time_range_start.isoformat(),
            "time_range_end": self.time_range_end.isoformat(),
            "summary": {
                "total_operations": self.total_operations,
                "total_documents": self.total_documents,
                "total_processing_time_ms": self.total_processing_time_ms,
                "average_processing_time_ms": self.average_processing_time_ms,
                "success_rate": self.success_rate,
                "error_rate": self.error_rate,
            },
            "performance": {
                "average_throughput_docs_per_second": self.average_throughput_docs_per_second,
                "average_throughput_chars_per_second": self.average_throughput_chars_per_second,
                "peak_throughput_docs_per_second": self.peak_throughput_docs_per_second,
                "peak_throughput_chars_per_second": self.peak_throughput_chars_per_second,
            },
            "usage": {
                "parser_usage": self.parser_usage,
                "chunking_strategy_usage": self.chunking_strategy_usage,
            },
            "errors": {
                "error_breakdown": self.error_breakdown,
                "total_errors": self.total_errors,
                "total_retries": self.total_retries,
            },
            "time_analysis": {
                "hourly_stats": self.hourly_stats,
                "daily_stats": self.daily_stats,
            },
            "quality": {
                "ocr_usage_rate": self.ocr_usage_rate,
                "text_cleaning_usage_rate": self.text_cleaning_usage_rate,
                "average_chunk_count_per_document": self.average_chunk_count_per_document,
            },
            "insights": self.insights,
            "recommendations": self.recommendations,
        }


class MetricsReporter:
    """Reporter for generating metrics reports and visualizations."""

    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize metrics reporter.

        Args:
            metrics_collector: MetricsCollector instance to report on
        """
        self.collector = metrics_collector
        self.logger = logger.bind(component="metrics_reporter")

    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        report_id: Optional[str] = None,
    ) -> MetricsReport:
        """Generate a comprehensive metrics report.

        Args:
            start_time: Start of time range (default: 24 hours ago)
            end_time: End of time range (default: now)
            report_id: Optional report identifier

        Returns:
            MetricsReport instance
        """
        now = datetime.utcnow()
        end_time = end_time or now
        start_time = start_time or (now - timedelta(days=1))
        report_id = report_id or f"report_{int(now.timestamp())}"

        # Get metrics in time range
        metrics_list = self.collector.get_metrics_in_timerange(start_time, end_time)

        # Create report
        report = MetricsReport(
            report_id=report_id,
            generated_at=now,
            time_range_start=start_time,
            time_range_end=end_time,
        )

        if not metrics_list:
            self.logger.warning(
                "no_metrics_in_timerange", start=start_time, end=end_time
            )
            return report

        # Calculate summary statistics
        self._calculate_summary_stats(report, metrics_list)

        # Calculate performance metrics
        self._calculate_performance_metrics(report, metrics_list)

        # Calculate usage statistics
        self._calculate_usage_stats(report, metrics_list)

        # Calculate error analysis
        self._calculate_error_analysis(report, metrics_list)

        # Calculate time-based analysis
        self._calculate_time_analysis(report, metrics_list)

        # Calculate quality metrics
        self._calculate_quality_metrics(report, metrics_list)

        # Generate insights and recommendations
        self._generate_insights(report, metrics_list)

        self.logger.info(
            "report_generated",
            report_id=report_id,
            operations=report.total_operations,
            time_range_hours=(end_time - start_time).total_seconds() / 3600,
        )

        return report

    def export_report(
        self, report: MetricsReport, output_path: str | Path, format: str = "json"
    ) -> bool:
        """Export report to file.

        Args:
            report: MetricsReport to export
            output_path: Path to save the report
            format: Export format ("json", "html", "csv")

        Returns:
            True if export was successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            elif format.lower() == "html":
                html_content = self._generate_html_report(report)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            elif format.lower() == "csv":
                csv_content = self._generate_csv_report(report)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(csv_content)

            else:
                raise ValueError(f"Unsupported format: {format}")

            self.logger.info(
                "report_exported",
                report_id=report.report_id,
                output_path=str(output_path),
                format=format,
            )

            return True

        except Exception as e:
            self.logger.error(
                "report_export_error",
                report_id=report.report_id,
                output_path=str(output_path),
                error=str(e),
            )
            return False

    def _calculate_summary_stats(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate summary statistics."""
        report.total_operations = len(metrics_list)
        report.total_documents = sum(m.document_count for m in metrics_list)
        report.total_processing_time_ms = sum(
            m.processing_time_ms for m in metrics_list
        )

        if report.total_operations > 0:
            report.average_processing_time_ms = (
                report.total_processing_time_ms / report.total_operations
            )

            successful_ops = sum(1 for m in metrics_list if m.error_count == 0)
            report.success_rate = successful_ops / report.total_operations
            report.error_rate = 1.0 - report.success_rate

    def _calculate_performance_metrics(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate performance metrics."""
        throughput_docs = [
            m.throughput_docs_per_second
            for m in metrics_list
            if m.throughput_docs_per_second > 0
        ]
        throughput_chars = [
            m.throughput_chars_per_second
            for m in metrics_list
            if m.throughput_chars_per_second > 0
        ]

        if throughput_docs:
            report.average_throughput_docs_per_second = sum(throughput_docs) / len(
                throughput_docs
            )
            report.peak_throughput_docs_per_second = max(throughput_docs)

        if throughput_chars:
            report.average_throughput_chars_per_second = sum(throughput_chars) / len(
                throughput_chars
            )
            report.peak_throughput_chars_per_second = max(throughput_chars)

    def _calculate_usage_stats(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate usage statistics."""
        parser_counts = {}
        chunking_counts = {}

        for metrics in metrics_list:
            if metrics.parser_used:
                parser_counts[metrics.parser_used] = (
                    parser_counts.get(metrics.parser_used, 0) + 1
                )

            if metrics.chunking_strategy:
                chunking_counts[metrics.chunking_strategy] = (
                    chunking_counts.get(metrics.chunking_strategy, 0) + 1
                )

        report.parser_usage = parser_counts
        report.chunking_strategy_usage = chunking_counts

    def _calculate_error_analysis(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate error analysis."""
        report.total_errors = sum(m.error_count for m in metrics_list)
        report.total_retries = sum(m.retry_count for m in metrics_list)

        # Get error breakdown from collector
        report.error_breakdown = dict(self.collector.error_types)

    def _calculate_time_analysis(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate time-based analysis."""
        hourly_stats = {}
        daily_stats = {}

        for metrics in metrics_list:
            if not metrics.start_time:
                continue

            # Hourly stats
            hour_key = metrics.start_time.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_stats:
                hourly_stats[hour_key] = {
                    "operations": 0,
                    "documents": 0,
                    "processing_time_ms": 0.0,
                    "errors": 0,
                }

            hourly_stats[hour_key]["operations"] += 1
            hourly_stats[hour_key]["documents"] += metrics.document_count
            hourly_stats[hour_key]["processing_time_ms"] += metrics.processing_time_ms
            hourly_stats[hour_key]["errors"] += metrics.error_count

            # Daily stats
            day_key = metrics.start_time.strftime("%Y-%m-%d")
            if day_key not in daily_stats:
                daily_stats[day_key] = {
                    "operations": 0,
                    "documents": 0,
                    "processing_time_ms": 0.0,
                    "errors": 0,
                }

            daily_stats[day_key]["operations"] += 1
            daily_stats[day_key]["documents"] += metrics.document_count
            daily_stats[day_key]["processing_time_ms"] += metrics.processing_time_ms
            daily_stats[day_key]["errors"] += metrics.error_count

        report.hourly_stats = hourly_stats
        report.daily_stats = daily_stats

    def _calculate_quality_metrics(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Calculate quality metrics."""
        if not metrics_list:
            return

        ocr_used_count = sum(1 for m in metrics_list if m.ocr_used)
        text_cleaning_count = sum(1 for m in metrics_list if m.text_cleaning_enabled)
        total_chunks = sum(m.total_chunk_count for m in metrics_list)

        report.ocr_usage_rate = ocr_used_count / len(metrics_list)
        report.text_cleaning_usage_rate = text_cleaning_count / len(metrics_list)

        if report.total_documents > 0:
            report.average_chunk_count_per_document = (
                total_chunks / report.total_documents
            )

    def _generate_insights(
        self, report: MetricsReport, metrics_list: List[ProcessingMetrics]
    ) -> None:
        """Generate insights and recommendations."""
        insights = []
        recommendations = []

        # Performance insights
        if report.average_processing_time_ms > 5000:  # 5 seconds
            insights.append("Processing times are higher than optimal")
            recommendations.append(
                "Consider optimizing parser selection or enabling parallel processing"
            )

        # Error rate insights
        if report.error_rate > 0.1:  # 10% error rate
            insights.append(f"High error rate detected: {report.error_rate:.1%}")
            recommendations.append(
                "Review error logs and consider improving input validation"
            )

        # OCR usage insights
        if report.ocr_usage_rate > 0.5:  # 50% OCR usage
            insights.append("High OCR usage indicates many scanned documents")
            recommendations.append(
                "Consider preprocessing scanned documents or using specialized OCR tools"
            )

        # Parser usage insights
        if report.parser_usage:
            most_used_parser = max(report.parser_usage, key=report.parser_usage.get)
            usage_percentage = (
                report.parser_usage[most_used_parser] / report.total_operations
            )
            if usage_percentage > 0.8:  # 80% usage of single parser
                insights.append(
                    f"Heavy reliance on {most_used_parser} parser ({usage_percentage:.1%})"
                )
                recommendations.append(
                    "Consider diversifying parser usage or optimizing the primary parser"
                )

        # Throughput insights
        if report.average_throughput_docs_per_second < 1.0:
            insights.append("Low document processing throughput")
            recommendations.append(
                "Consider batch processing or performance optimization"
            )

        report.insights = insights
        report.recommendations = recommendations

    def _generate_html_report(self, report: MetricsReport) -> str:
        """Generate HTML report."""
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Data Pipelines Metrics Report - {report.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
        .insight {{ background-color: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 3px; }}
        .recommendation {{ background-color: #d1ecf1; padding: 10px; margin: 5px 0; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Data Pipelines Metrics Report</h1>
        <p><strong>Report ID:</strong> {report.report_id}</p>
        <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Time Range:</strong> {report.time_range_start.strftime('%Y-%m-%d %H:%M')} - {report.time_range_end.strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="section">
        <h2>Summary Statistics</h2>
        <div class="metric"><strong>Total Operations:</strong> {report.total_operations}</div>
        <div class="metric"><strong>Total Documents:</strong> {report.total_documents}</div>
        <div class="metric"><strong>Success Rate:</strong> {report.success_rate:.1%}</div>
        <div class="metric"><strong>Average Processing Time:</strong> {report.average_processing_time_ms:.1f}ms</div>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
        <div class="metric"><strong>Avg Throughput:</strong> {report.average_throughput_docs_per_second:.2f} docs/sec</div>
        <div class="metric"><strong>Peak Throughput:</strong> {report.peak_throughput_docs_per_second:.2f} docs/sec</div>
    </div>
    
    <div class="section">
        <h2>Usage Statistics</h2>
        <h3>Parser Usage</h3>
        <table>
            <tr><th>Parser</th><th>Usage Count</th></tr>
            {''.join(f'<tr><td>{parser}</td><td>{count}</td></tr>' for parser, count in report.parser_usage.items())}
        </table>
        
        <h3>Chunking Strategy Usage</h3>
        <table>
            <tr><th>Strategy</th><th>Usage Count</th></tr>
            {''.join(f'<tr><td>{strategy}</td><td>{count}</td></tr>' for strategy, count in report.chunking_strategy_usage.items())}
        </table>
    </div>
    
    <div class="section">
        <h2>Insights</h2>
        {''.join(f'<div class="insight">💡 {insight}</div>' for insight in report.insights)}
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        {''.join(f'<div class="recommendation">🎯 {rec}</div>' for rec in report.recommendations)}
    </div>
</body>
</html>
        """
        return html_template

    def _generate_csv_report(self, report: MetricsReport) -> str:
        """Generate CSV report."""
        lines = [
            "Metric,Value",
            f"Report ID,{report.report_id}",
            f"Generated At,{report.generated_at.isoformat()}",
            f"Time Range Start,{report.time_range_start.isoformat()}",
            f"Time Range End,{report.time_range_end.isoformat()}",
            f"Total Operations,{report.total_operations}",
            f"Total Documents,{report.total_documents}",
            f"Success Rate,{report.success_rate:.3f}",
            f"Average Processing Time (ms),{report.average_processing_time_ms:.1f}",
            f"Average Throughput (docs/sec),{report.average_throughput_docs_per_second:.2f}",
            f"Peak Throughput (docs/sec),{report.peak_throughput_docs_per_second:.2f}",
            f"Total Errors,{report.total_errors}",
            f"Total Retries,{report.total_retries}",
            f"OCR Usage Rate,{report.ocr_usage_rate:.3f}",
            f"Text Cleaning Usage Rate,{report.text_cleaning_usage_rate:.3f}",
        ]

        return "\n".join(lines)
