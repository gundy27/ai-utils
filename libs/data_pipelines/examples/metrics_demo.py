"""Example demonstrating the metrics and observability system."""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
)
from gundy_ai.data_pipelines.metrics import (
    MetricsCollector,
    MetricsReporter,
    MetricsDashboard,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertCondition,
)


async def simulate_processing_workload(
    doc_processor: EnhancedDocumentProcessor,
    chunker: EnhancedTextChunker,
    metrics_collector: MetricsCollector,
    num_documents: int = 10,
) -> None:
    """Simulate a processing workload with metrics collection."""

    # Sample documents with varying complexity
    documents = [
        "Short document for testing.",
        """
        Medium length document with multiple paragraphs.
        
        This document has several sentences and should demonstrate
        normal processing behavior with reasonable performance metrics.
        
        It includes multiple paragraphs to test chunking strategies
        and provides a good baseline for metrics collection.
        """,
        """
        # Long Technical Document
        
        This is a comprehensive technical document that will take longer to process
        and generate more chunks. It's designed to test the metrics system under
        more realistic conditions.
        
        ## Section 1: Introduction
        
        Technical documents often contain complex structures, multiple sections,
        and detailed information that requires careful processing. This document
        simulates such content to provide meaningful metrics.
        
        ## Section 2: Detailed Analysis
        
        The processing of technical documents involves several stages:
        1. Document parsing and text extraction
        2. Text cleaning and normalization
        3. Semantic chunking for optimal retrieval
        4. Quality assessment and validation
        
        Each stage contributes to the overall processing time and affects
        the quality of the final output. Monitoring these metrics helps
        identify bottlenecks and optimization opportunities.
        
        ## Section 3: Performance Considerations
        
        When processing large volumes of documents, performance becomes critical.
        Key metrics to monitor include:
        - Processing time per document
        - Throughput (documents per second)
        - Error rates and retry counts
        - Resource utilization
        
        ## Conclusion
        
        Comprehensive metrics collection enables data-driven optimization
        of document processing pipelines and ensures reliable operation
        at scale.
        """
        * 2,  # Make it even longer
    ]

    for i in range(num_documents):
        # Select document based on index to create variety
        doc_content = documents[i % len(documents)]

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(doc_content)
            temp_file = f.name

        try:
            # Start metrics tracking
            operation_id = f"doc_processing_{i}"
            metrics_collector.start_processing(
                operation_id,
                document_index=i,
                document_type="text",
                source="simulation",
            )

            # Process document
            doc_result = await doc_processor.process(temp_file)

            if doc_result.success:
                document = doc_result.data

                # Update metrics with document processing results
                metrics_collector.update_processing_metrics(
                    operation_id,
                    document_count=1,
                    total_text_length=len(document.full_text),
                    total_word_count=document.metadata.word_count or 0,
                    parser_used="text_parser",
                )

                # Chunk the document
                chunk_result = await chunker.process(document)

                if chunk_result.success:
                    chunked_doc = chunk_result.data

                    # Update metrics with chunking results
                    metrics_collector.update_processing_metrics(
                        operation_id,
                        total_chunk_count=len(chunked_doc.chunks),
                        chunking_strategy="structure_aware",
                    )

                    # Finish successful processing
                    metrics_collector.finish_processing(operation_id, success=True)
                else:
                    # Chunking failed
                    metrics_collector.finish_processing(
                        operation_id, success=False, error_type="chunking_error"
                    )
            else:
                # Document processing failed
                metrics_collector.finish_processing(
                    operation_id, success=False, error_type="document_processing_error"
                )

            # Simulate some processing delay
            await asyncio.sleep(0.1)

        finally:
            # Cleanup
            Path(temp_file).unlink(missing_ok=True)

        # Occasionally simulate errors for demonstration
        if i % 7 == 0 and i > 0:  # Every 7th document after the first
            error_operation_id = f"error_simulation_{i}"
            metrics_collector.start_processing(
                error_operation_id,
                document_index=i,
                document_type="text",
                source="error_simulation",
            )

            # Simulate processing time before error
            await asyncio.sleep(0.05)

            # Record error
            metrics_collector.record_error("simulated_error", error_operation_id)
            metrics_collector.finish_processing(
                error_operation_id, success=False, error_type="simulated_error"
            )


async def main():
    """Demonstrate the metrics and observability system."""
    print("📊 Metrics and Observability Demo")
    print("=" * 60)

    # Initialize components
    print("🔧 Initializing components...")

    # Metrics collector
    metrics_collector = MetricsCollector(max_history=100)

    # Metrics reporter
    metrics_reporter = MetricsReporter(metrics_collector)

    # Dashboard
    dashboard = MetricsDashboard(metrics_collector)

    # Alert manager
    alert_manager = AlertManager(metrics_collector)

    # Document processing components
    doc_config = ProcessorConfig(name="metrics_demo_doc")
    doc_processor = EnhancedDocumentProcessor(doc_config)

    chunker_config = ProcessorConfig(name="metrics_demo_chunker")
    chunker = EnhancedTextChunker(
        config=chunker_config, strategy="structure_aware", chunk_size=300
    )

    print("✅ Components initialized")
    print()

    # Add custom alert rule
    print("🚨 Setting up custom alert rules...")

    custom_rule = AlertRule(
        rule_id="demo_high_processing_time",
        name="Demo High Processing Time",
        description="Alert when processing time exceeds 2 seconds (demo threshold)",
        severity=AlertSeverity.WARNING,
        metric_path="avg_processing_time_ms",
        condition=AlertCondition.GREATER_THAN,
        threshold_value=2000,  # 2 seconds (low for demo)
        evaluation_window_minutes=1,
        cooldown_minutes=2,
    )

    alert_manager.add_rule(custom_rule)
    print(f"✅ Added custom alert rule: {custom_rule.name}")
    print()

    # Simulate processing workload
    print("🔄 Simulating document processing workload...")
    print("   Processing 15 documents with varying complexity...")

    await simulate_processing_workload(
        doc_processor, chunker, metrics_collector, num_documents=15
    )

    print("✅ Workload simulation completed")
    print()

    # Show real-time metrics
    print("📈 Real-time Metrics:")
    real_time_metrics = dashboard.get_real_time_metrics()

    print("   Last 5 minutes:")
    print(
        f"     Operations/min: {real_time_metrics['last_5_minutes']['operations_per_minute']:.1f}"
    )
    print(
        f"     Documents/min: {real_time_metrics['last_5_minutes']['documents_per_minute']:.1f}"
    )
    print(
        f"     Avg processing time: {real_time_metrics['last_5_minutes']['average_processing_time_ms']:.1f}ms"
    )
    print(f"     Error rate: {real_time_metrics['last_5_minutes']['error_rate']:.1%}")
    print()

    # Show system overview
    print("🔍 System Overview:")
    overview = dashboard.get_system_overview()

    print(f"   Total operations: {overview['system_stats']['total_operations']}")
    print(f"   Total documents: {overview['system_stats']['total_documents']}")
    print(
        f"   Overall success rate: {overview['system_stats']['overall_success_rate']:.1%}"
    )
    print(
        f"   Total processing time: {overview['system_stats']['total_processing_time_hours']:.3f} hours"
    )
    print()

    print("   Performance:")
    print(
        f"     Recent avg processing time: {overview['performance']['recent_avg_processing_time_ms']:.1f}ms"
    )
    print(
        f"     Recent success rate: {overview['performance']['recent_success_rate']:.1%}"
    )
    print(
        f"     Avg throughput: {overview['performance']['average_throughput_docs_per_second']:.2f} docs/sec"
    )
    print()

    # Show usage patterns
    if overview["usage_patterns"]["top_parsers"]:
        print("   Top parsers:")
        for parser, count in overview["usage_patterns"]["top_parsers"]:
            print(f"     {parser}: {count} uses")

    if overview["usage_patterns"]["top_chunking_strategies"]:
        print("   Top chunking strategies:")
        for strategy, count in overview["usage_patterns"]["top_chunking_strategies"]:
            print(f"     {strategy}: {count} uses")
    print()

    # Evaluate alerts
    print("🚨 Alert Evaluation:")
    new_alerts = alert_manager.evaluate_rules()

    if new_alerts:
        print(f"   {len(new_alerts)} new alerts triggered:")
        for alert in new_alerts:
            print(f"     🔔 {alert.severity.value.upper()}: {alert.message}")
    else:
        print("   No new alerts triggered")

    # Show alert summary
    alert_summary = alert_manager.get_alert_summary()
    print(f"   Active alerts: {alert_summary['active_alerts']['total']}")
    print(f"   Recent alerts (24h): {alert_summary['recent_alerts_24h']['total']}")
    print(
        f"   Alert rules: {alert_summary['rules']['enabled']}/{alert_summary['rules']['total']} enabled"
    )
    print()

    # Generate comprehensive report
    print("📋 Generating Metrics Report...")

    # Generate report for the last hour (or since start)
    report_start = datetime.utcnow() - timedelta(hours=1)
    report = metrics_reporter.generate_report(
        start_time=report_start, report_id="demo_report"
    )

    print(f"✅ Report generated: {report.report_id}")
    print(
        f"   Time range: {report.time_range_start.strftime('%H:%M')} - {report.time_range_end.strftime('%H:%M')}"
    )
    print(f"   Operations: {report.total_operations}")
    print(f"   Documents: {report.total_documents}")
    print(f"   Success rate: {report.success_rate:.1%}")
    print(f"   Avg processing time: {report.average_processing_time_ms:.1f}ms")
    print()

    # Show insights and recommendations
    if report.insights:
        print("💡 Insights:")
        for insight in report.insights:
            print(f"   • {insight}")

    if report.recommendations:
        print("🎯 Recommendations:")
        for recommendation in report.recommendations:
            print(f"   • {recommendation}")
    print()

    # Export reports
    with tempfile.TemporaryDirectory() as temp_dir:
        print("💾 Exporting Reports...")

        # Export JSON report
        json_path = Path(temp_dir) / "metrics_report.json"
        json_success = metrics_reporter.export_report(report, json_path, "json")

        # Export HTML report
        html_path = Path(temp_dir) / "metrics_report.html"
        html_success = metrics_reporter.export_report(report, html_path, "html")

        # Export dashboard HTML
        dashboard_path = Path(temp_dir) / "dashboard.html"
        dashboard_html = dashboard.generate_dashboard_html()
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(dashboard_html)

        print(
            f"   JSON report: {'✅' if json_success else '❌'} ({json_path.stat().st_size if json_success else 0} bytes)"
        )
        print(
            f"   HTML report: {'✅' if html_success else '❌'} ({html_path.stat().st_size if html_success else 0} bytes)"
        )
        print(f"   Dashboard: ✅ ({dashboard_path.stat().st_size} bytes)")

        # Show file previews
        if json_success:
            print(f"   JSON report preview: {str(json_path)}")

        if html_success:
            print(f"   HTML report preview: {str(html_path)}")

        print(f"   Dashboard preview: {str(dashboard_path)}")
        print()

    # Show current system status
    print("🏥 Current System Status:")
    status = dashboard.get_current_status()

    print(f"   Health: {status['health_status'].upper()}")
    print(f"   Active operations: {status['active_operations']}")
    print(f"   Recent error rate: {status['recent_error_rate']:.1%}")

    if status["current_operations"]:
        print("   Current operations:")
        for op in status["current_operations"][:3]:  # Show first 3
            print(f"     • {op['operation_id'][:12]}... ({op['document_count']} docs)")
    print()

    print("🎯 Key Benefits of Metrics System:")
    print("   • Real-time monitoring of processing performance")
    print("   • Automated alerting for system issues")
    print("   • Comprehensive reporting with insights")
    print("   • Historical trend analysis")
    print("   • Customizable dashboards and alerts")
    print("   • Export capabilities for external systems")
    print()

    print("💡 Production Use Cases:")
    print("   • Monitor document processing pipelines")
    print("   • Detect performance degradation early")
    print("   • Optimize parser and chunking strategies")
    print("   • Track system reliability and uptime")
    print("   • Generate compliance and audit reports")
    print("   • Capacity planning and scaling decisions")


if __name__ == "__main__":
    asyncio.run(main())
