"""Alert system for monitoring data pipelines metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from .collector import MetricsCollector

logger = structlog.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCondition(Enum):
    """Alert condition types."""

    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    THRESHOLD_EXCEEDED = "threshold_exceeded"


@dataclass
class AlertRule:
    """Definition of an alert rule."""

    rule_id: str
    name: str
    description: str
    severity: AlertSeverity

    # Condition definition
    metric_path: str  # e.g., "error_rate", "performance.avg_processing_time_ms"
    condition: AlertCondition
    threshold_value: Any

    # Evaluation settings
    evaluation_window_minutes: int = 5
    min_data_points: int = 1

    # Alert settings
    cooldown_minutes: int = 15  # Minimum time between alerts
    enabled: bool = True

    # Optional custom evaluation function
    custom_evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class Alert:
    """An active alert."""

    alert_id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    metric_value: Any
    threshold_value: Any
    resolved_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.resolved_at is None

    @property
    def duration_minutes(self) -> float:
        """Get alert duration in minutes."""
        end_time = self.resolved_at or datetime.utcnow()
        return (end_time - self.triggered_at).total_seconds() / 60


class AlertManager:
    """Manager for monitoring alerts and notifications."""

    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize alert manager.

        Args:
            metrics_collector: MetricsCollector to monitor
        """
        self.collector = metrics_collector
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.last_rule_evaluation: Dict[str, datetime] = {}

        self.logger = logger.bind(component="alert_manager")

        # Register default rules
        self._register_default_rules()

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule.

        Args:
            rule: AlertRule to add
        """
        self.rules[rule.rule_id] = rule
        self.logger.info("alert_rule_added", rule_id=rule.rule_id, name=rule.name)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.

        Args:
            rule_id: ID of the rule to remove

        Returns:
            True if rule was removed
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.logger.info("alert_rule_removed", rule_id=rule_id)
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable an alert rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            self.logger.info("alert_rule_enabled", rule_id=rule_id)
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable an alert rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            self.logger.info("alert_rule_disabled", rule_id=rule_id)
            return True
        return False

    def evaluate_rules(self) -> List[Alert]:
        """Evaluate all alert rules and return new alerts.

        Returns:
            List of newly triggered alerts
        """
        new_alerts = []
        now = datetime.utcnow()

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Check cooldown
            last_eval = self.last_rule_evaluation.get(rule.rule_id)
            if last_eval and (now - last_eval).total_seconds() < 60:  # 1 minute minimum
                continue

            try:
                alert = self._evaluate_rule(rule, now)
                if alert:
                    new_alerts.append(alert)
                    self.active_alerts[alert.alert_id] = alert
                    self.alert_history.append(alert)

                    self.logger.warning(
                        "alert_triggered",
                        alert_id=alert.alert_id,
                        rule_id=rule.rule_id,
                        severity=alert.severity.value,
                        message=alert.message,
                    )

                self.last_rule_evaluation[rule.rule_id] = now

            except Exception as e:
                self.logger.error(
                    "alert_rule_evaluation_error", rule_id=rule.rule_id, error=str(e)
                )

        return new_alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert.

        Args:
            alert_id: ID of the alert to resolve

        Returns:
            True if alert was resolved
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            del self.active_alerts[alert_id]

            self.logger.info(
                "alert_resolved",
                alert_id=alert_id,
                duration_minutes=alert.duration_minutes,
            )
            return True
        return False

    def get_active_alerts(
        self, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts, optionally filtered by severity.

        Args:
            severity: Optional severity filter

        Returns:
            List of active alerts
        """
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_alert_history(
        self, hours: int = 24, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alert history.

        Args:
            hours: Number of hours of history to return
            severity: Optional severity filter

        Returns:
            List of historical alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts = [
            alert for alert in self.alert_history if alert.triggered_at >= cutoff_time
        ]

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics.

        Returns:
            Dictionary with alert statistics
        """
        active_alerts = self.get_active_alerts()
        recent_alerts = self.get_alert_history(24)  # Last 24 hours

        # Count by severity
        active_by_severity = {}
        recent_by_severity = {}

        for severity in AlertSeverity:
            active_by_severity[severity.value] = len(
                [a for a in active_alerts if a.severity == severity]
            )
            recent_by_severity[severity.value] = len(
                [a for a in recent_alerts if a.severity == severity]
            )

        # Rule statistics
        enabled_rules = sum(1 for rule in self.rules.values() if rule.enabled)
        total_rules = len(self.rules)

        return {
            "active_alerts": {
                "total": len(active_alerts),
                "by_severity": active_by_severity,
            },
            "recent_alerts_24h": {
                "total": len(recent_alerts),
                "by_severity": recent_by_severity,
            },
            "rules": {
                "total": total_rules,
                "enabled": enabled_rules,
                "disabled": total_rules - enabled_rules,
            },
            "oldest_active_alert": min(
                (alert.triggered_at for alert in active_alerts), default=None
            ),
        }

    def _evaluate_rule(
        self, rule: AlertRule, evaluation_time: datetime
    ) -> Optional[Alert]:
        """Evaluate a single alert rule.

        Args:
            rule: AlertRule to evaluate
            evaluation_time: Time of evaluation

        Returns:
            Alert if rule is triggered, None otherwise
        """
        # Check if we're in cooldown period
        for alert in self.active_alerts.values():
            if (
                alert.rule_id == rule.rule_id
                and (evaluation_time - alert.triggered_at).total_seconds()
                < rule.cooldown_minutes * 60
            ):
                return None

        # Get evaluation data
        window_start = evaluation_time - timedelta(
            minutes=rule.evaluation_window_minutes
        )
        metrics_in_window = self.collector.get_metrics_in_timerange(
            window_start, evaluation_time
        )

        if len(metrics_in_window) < rule.min_data_points:
            return None

        # Use custom evaluator if provided
        if rule.custom_evaluator:
            try:
                evaluation_data = {
                    "metrics": metrics_in_window,
                    "aggregated_stats": self.collector.get_aggregated_stats(),
                    "performance_summary": self.collector.get_performance_summary(),
                }

                if rule.custom_evaluator(evaluation_data):
                    return self._create_alert(
                        rule, evaluation_time, "Custom condition met", None
                    )
            except Exception as e:
                self.logger.error(
                    "custom_evaluator_error", rule_id=rule.rule_id, error=str(e)
                )
            return None

        # Standard metric evaluation
        metric_value = self._extract_metric_value(metrics_in_window, rule.metric_path)
        if metric_value is None:
            return None

        # Evaluate condition
        condition_met = self._evaluate_condition(
            metric_value, rule.condition, rule.threshold_value
        )

        if condition_met:
            message = self._generate_alert_message(rule, metric_value)
            return self._create_alert(rule, evaluation_time, message, metric_value)

        return None

    def _extract_metric_value(self, metrics_list: List[Any], metric_path: str) -> Any:
        """Extract metric value from metrics list."""
        if not metrics_list:
            return None

        # Handle common metric paths
        if metric_path == "error_rate":
            errors = sum(1 for m in metrics_list if m.error_count > 0)
            return errors / len(metrics_list)

        elif metric_path == "avg_processing_time_ms":
            return sum(m.processing_time_ms for m in metrics_list) / len(metrics_list)

        elif metric_path == "throughput_docs_per_second":
            throughputs = [
                m.throughput_docs_per_second
                for m in metrics_list
                if m.throughput_docs_per_second > 0
            ]
            return sum(throughputs) / len(throughputs) if throughputs else 0.0

        elif metric_path == "ocr_usage_rate":
            ocr_used = sum(1 for m in metrics_list if m.ocr_used)
            return ocr_used / len(metrics_list)

        # Add more metric paths as needed
        return None

    def _evaluate_condition(
        self, value: Any, condition: AlertCondition, threshold: Any
    ) -> bool:
        """Evaluate alert condition."""
        try:
            if condition == AlertCondition.GREATER_THAN:
                return value > threshold
            elif condition == AlertCondition.LESS_THAN:
                return value < threshold
            elif condition == AlertCondition.EQUALS:
                return value == threshold
            elif condition == AlertCondition.NOT_EQUALS:
                return value != threshold
            elif condition == AlertCondition.CONTAINS:
                return threshold in str(value)
            elif condition == AlertCondition.THRESHOLD_EXCEEDED:
                return value > threshold
        except Exception:
            return False

        return False

    def _generate_alert_message(self, rule: AlertRule, metric_value: Any) -> str:
        """Generate alert message."""
        return (
            f"{rule.name}: {rule.metric_path} is {metric_value} "
            f"({rule.condition.value} {rule.threshold_value})"
        )

    def _create_alert(
        self, rule: AlertRule, triggered_at: datetime, message: str, metric_value: Any
    ) -> Alert:
        """Create a new alert."""
        alert_id = f"{rule.rule_id}_{int(triggered_at.timestamp())}"

        return Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            triggered_at=triggered_at,
            metric_value=metric_value,
            threshold_value=rule.threshold_value,
        )

    def _register_default_rules(self) -> None:
        """Register default alert rules."""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Alert when error rate exceeds 10%",
                severity=AlertSeverity.WARNING,
                metric_path="error_rate",
                condition=AlertCondition.GREATER_THAN,
                threshold_value=0.1,
                evaluation_window_minutes=5,
                cooldown_minutes=15,
            ),
            AlertRule(
                rule_id="critical_error_rate",
                name="Critical Error Rate",
                description="Alert when error rate exceeds 50%",
                severity=AlertSeverity.CRITICAL,
                metric_path="error_rate",
                condition=AlertCondition.GREATER_THAN,
                threshold_value=0.5,
                evaluation_window_minutes=5,
                cooldown_minutes=10,
            ),
            AlertRule(
                rule_id="slow_processing",
                name="Slow Processing",
                description="Alert when average processing time exceeds 10 seconds",
                severity=AlertSeverity.WARNING,
                metric_path="avg_processing_time_ms",
                condition=AlertCondition.GREATER_THAN,
                threshold_value=10000,  # 10 seconds
                evaluation_window_minutes=10,
                cooldown_minutes=20,
            ),
            AlertRule(
                rule_id="low_throughput",
                name="Low Throughput",
                description="Alert when throughput drops below 0.1 docs/second",
                severity=AlertSeverity.WARNING,
                metric_path="throughput_docs_per_second",
                condition=AlertCondition.LESS_THAN,
                threshold_value=0.1,
                evaluation_window_minutes=15,
                cooldown_minutes=30,
            ),
        ]

        for rule in default_rules:
            self.add_rule(rule)
