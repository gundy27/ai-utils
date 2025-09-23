"""Simple metrics dashboard for monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import structlog

from .collector import MetricsCollector
from .reporter import MetricsReporter

logger = structlog.get_logger(__name__)


class MetricsDashboard:
    """Simple dashboard for monitoring data pipelines metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize metrics dashboard.

        Args:
            metrics_collector: MetricsCollector instance to monitor
        """
        self.collector = metrics_collector
        self.reporter = MetricsReporter(metrics_collector)
        self.logger = logger.bind(component="metrics_dashboard")

    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status."""
        current_metrics = self.collector.get_current_metrics()
        recent_metrics = self.collector.get_recent_metrics(10)
        performance_summary = self.collector.get_performance_summary()

        # Calculate current load
        active_operations = len(current_metrics)

        # Get recent error rate
        recent_errors = sum(1 for m in recent_metrics if m.error_count > 0)
        recent_error_rate = (
            recent_errors / len(recent_metrics) if recent_metrics else 0.0
        )

        # Determine system health
        health_status = self._determine_health_status(
            active_operations, recent_error_rate, performance_summary
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": health_status,
            "active_operations": active_operations,
            "recent_error_rate": recent_error_rate,
            "performance_summary": performance_summary,
            "current_operations": [
                {
                    "operation_id": op_id,
                    "start_time": metrics.start_time.isoformat(),
                    "document_count": metrics.document_count,
                    "parser_used": metrics.parser_used,
                }
                for op_id, metrics in current_metrics.items()
            ],
        }

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics for monitoring."""
        now = datetime.utcnow()
        last_5_minutes = now - timedelta(minutes=5)
        last_hour = now - timedelta(hours=1)

        recent_5min = self.collector.get_metrics_in_timerange(last_5_minutes, now)
        recent_hour = self.collector.get_metrics_in_timerange(last_hour, now)

        def calculate_rate_metrics(metrics_list: List[Any]) -> Dict[str, float]:
            if not metrics_list:
                return {
                    "operations_per_minute": 0.0,
                    "documents_per_minute": 0.0,
                    "average_processing_time_ms": 0.0,
                    "error_rate": 0.0,
                }

            duration_minutes = 5.0 if metrics_list == recent_5min else 60.0

            operations_per_minute = len(metrics_list) / duration_minutes
            documents_per_minute = (
                sum(m.document_count for m in metrics_list) / duration_minutes
            )
            avg_processing_time = sum(m.processing_time_ms for m in metrics_list) / len(
                metrics_list
            )
            error_rate = sum(1 for m in metrics_list if m.error_count > 0) / len(
                metrics_list
            )

            return {
                "operations_per_minute": operations_per_minute,
                "documents_per_minute": documents_per_minute,
                "average_processing_time_ms": avg_processing_time,
                "error_rate": error_rate,
            }

        return {
            "timestamp": now.isoformat(),
            "last_5_minutes": calculate_rate_metrics(recent_5min),
            "last_hour": calculate_rate_metrics(recent_hour),
            "active_operations": len(self.collector.get_current_metrics()),
        }

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview with key metrics."""
        aggregated_stats = self.collector.get_aggregated_stats()

        # Top parsers and strategies
        top_parsers = sorted(
            aggregated_stats["parser_usage"].items(), key=lambda x: x[1], reverse=True
        )[:5]

        top_strategies = sorted(
            aggregated_stats["chunking_strategy_usage"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Recent trends
        recent_metrics = self.collector.get_recent_metrics(50)
        if recent_metrics:
            recent_avg_time = sum(m.processing_time_ms for m in recent_metrics) / len(
                recent_metrics
            )
            recent_success_rate = sum(
                1 for m in recent_metrics if m.error_count == 0
            ) / len(recent_metrics)
        else:
            recent_avg_time = 0.0
            recent_success_rate = 1.0

        return {
            "system_stats": {
                "total_operations": aggregated_stats["total_operations"],
                "total_documents": aggregated_stats["total_documents"],
                "overall_success_rate": 1.0 - aggregated_stats["error_rate"],
                "total_processing_time_hours": aggregated_stats[
                    "total_processing_time_ms"
                ]
                / (1000 * 3600),
            },
            "performance": {
                "recent_avg_processing_time_ms": recent_avg_time,
                "recent_success_rate": recent_success_rate,
                "average_throughput_docs_per_second": aggregated_stats[
                    "average_throughput_docs_per_second"
                ],
                "average_throughput_chars_per_second": aggregated_stats[
                    "average_throughput_chars_per_second"
                ],
            },
            "usage_patterns": {
                "top_parsers": top_parsers,
                "top_chunking_strategies": top_strategies,
            },
            "error_analysis": {
                "total_errors": aggregated_stats["total_errors"],
                "total_retries": aggregated_stats["total_retries"],
                "error_breakdown": aggregated_stats["error_breakdown"],
            },
        }

    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard."""
        status = self.get_current_status()
        overview = self.get_system_overview()
        real_time = self.get_real_time_metrics()

        # Determine status color
        status_colors = {
            "healthy": "#28a745",
            "warning": "#ffc107",
            "critical": "#dc3545",
        }
        status_color = status_colors.get(status["health_status"], "#6c757d")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Data Pipelines Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
        .header {{ background-color: #343a40; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .status-badge {{ 
            display: inline-block; 
            padding: 5px 15px; 
            background-color: {status_color}; 
            color: white; 
            border-radius: 20px; 
            font-weight: bold; 
        }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .metric-value {{ font-weight: bold; color: #007bff; }}
        .operations-list {{ max-height: 200px; overflow-y: auto; }}
        .operation-item {{ padding: 5px; border-bottom: 1px solid #eee; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Data Pipelines Dashboard</h1>
        <span class="status-badge">{status["health_status"].upper()}</span>
        <span class="timestamp">Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
    </div>
    
    <div class="dashboard-grid">
        <div class="card">
            <h3>System Status</h3>
            <div class="metric">
                <span>Active Operations:</span>
                <span class="metric-value">{status["active_operations"]}</span>
            </div>
            <div class="metric">
                <span>Recent Error Rate:</span>
                <span class="metric-value">{status["recent_error_rate"]:.1%}</span>
            </div>
            <div class="metric">
                <span>Operations/min (5min):</span>
                <span class="metric-value">{real_time["last_5_minutes"]["operations_per_minute"]:.1f}</span>
            </div>
            <div class="metric">
                <span>Documents/min (5min):</span>
                <span class="metric-value">{real_time["last_5_minutes"]["documents_per_minute"]:.1f}</span>
            </div>
        </div>
        
        <div class="card">
            <h3>Performance Summary</h3>
            <div class="metric">
                <span>Avg Processing Time:</span>
                <span class="metric-value">{overview["performance"]["recent_avg_processing_time_ms"]:.1f}ms</span>
            </div>
            <div class="metric">
                <span>Recent Success Rate:</span>
                <span class="metric-value">{overview["performance"]["recent_success_rate"]:.1%}</span>
            </div>
            <div class="metric">
                <span>Throughput (docs/sec):</span>
                <span class="metric-value">{overview["performance"]["average_throughput_docs_per_second"]:.2f}</span>
            </div>
        </div>
        
        <div class="card">
            <h3>System Overview</h3>
            <div class="metric">
                <span>Total Operations:</span>
                <span class="metric-value">{overview["system_stats"]["total_operations"]:,}</span>
            </div>
            <div class="metric">
                <span>Total Documents:</span>
                <span class="metric-value">{overview["system_stats"]["total_documents"]:,}</span>
            </div>
            <div class="metric">
                <span>Overall Success Rate:</span>
                <span class="metric-value">{overview["system_stats"]["overall_success_rate"]:.1%}</span>
            </div>
            <div class="metric">
                <span>Total Processing Hours:</span>
                <span class="metric-value">{overview["system_stats"]["total_processing_time_hours"]:.1f}</span>
            </div>
        </div>
        
        <div class="card">
            <h3>Active Operations</h3>
            <div class="operations-list">
                {''.join(f'''
                <div class="operation-item">
                    <strong>{op["operation_id"][:8]}...</strong><br>
                    Started: {datetime.fromisoformat(op["start_time"]).strftime('%H:%M:%S')}<br>
                    Documents: {op["document_count"]}, Parser: {op["parser_used"] or "N/A"}
                </div>
                ''' for op in status["current_operations"][:10])}
                {f'<div class="operation-item">... and {len(status["current_operations"]) - 10} more</div>' if len(status["current_operations"]) > 10 else ''}
            </div>
        </div>
        
        <div class="card">
            <h3>Top Parsers</h3>
            <table>
                <tr><th>Parser</th><th>Usage</th></tr>
                {''.join(f'<tr><td>{parser}</td><td>{count}</td></tr>' for parser, count in overview["usage_patterns"]["top_parsers"])}
            </table>
        </div>
        
        <div class="card">
            <h3>Error Analysis</h3>
            <div class="metric">
                <span>Total Errors:</span>
                <span class="metric-value">{overview["error_analysis"]["total_errors"]}</span>
            </div>
            <div class="metric">
                <span>Total Retries:</span>
                <span class="metric-value">{overview["error_analysis"]["total_retries"]}</span>
            </div>
            <table>
                <tr><th>Error Type</th><th>Count</th></tr>
                {''.join(f'<tr><td>{error_type}</td><td>{count}</td></tr>' for error_type, count in list(overview["error_analysis"]["error_breakdown"].items())[:5])}
            </table>
        </div>
    </div>
</body>
</html>
        """

        return html

    def _determine_health_status(
        self,
        active_operations: int,
        recent_error_rate: float,
        performance_summary: Dict[str, Any],
    ) -> str:
        """Determine system health status."""
        # Critical conditions
        if recent_error_rate > 0.5:  # 50% error rate
            return "critical"

        if active_operations > 100:  # Too many concurrent operations
            return "critical"

        # Warning conditions
        if recent_error_rate > 0.1:  # 10% error rate
            return "warning"

        if active_operations > 50:  # High load
            return "warning"

        # Check performance degradation
        last_hour_stats = performance_summary.get("last_hour", {})
        if last_hour_stats.get("success_rate", 1.0) < 0.9:  # 90% success rate
            return "warning"

        return "healthy"
