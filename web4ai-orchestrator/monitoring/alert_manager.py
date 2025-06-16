# monitoring/alert_manager.py - Advanced Monitoring and Alerting
"""
Advanced monitoring and alerting system for Web4AI Orchestrator
Provides real-time metrics, threshold monitoring, and multi-channel alerting
"""

import smtplib
import json
import time
import asyncio
import logging
import statistics
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import threading
from collections import defaultdict, deque
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning" 
    INFO = "info"
    DEBUG = "debug"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    metric_name: str
    metric_value: float
    threshold_value: float
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

class MetricCollector:
    """Collect and store metrics from orchestrator components"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.prometheus_metrics = self._setup_prometheus_metrics()
        
    def _setup_prometheus_metrics(self) -> Dict[str, Any]:
        """Setup Prometheus metrics"""
        return {
            # Counters
            'requests_total': Counter('web4ai_requests_total', 'Total requests', ['method', 'endpoint', 'status']),
            'tasks_total': Counter('web4ai_tasks_total', 'Total tasks', ['type', 'status']),
            'node_failures_total': Counter('web4ai_node_failures_total', 'Total node failures', ['node_id']),
            
            # Gauges
            'active_nodes': Gauge('web4ai_active_nodes', 'Number of active nodes'),
            'pending_tasks': Gauge('web4ai_pending_tasks', 'Number of pending tasks'),
            'network_utilization': Gauge('web4ai_network_utilization', 'Network utilization percentage'),
            'node_cpu_usage': Gauge('web4ai_node_cpu_usage', 'Node CPU usage', ['node_id']),
            'node_memory_usage': Gauge('web4ai_node_memory_usage', 'Node memory usage', ['node_id']),
            
            # Histograms
            'task_duration': Histogram('web4ai_task_duration_seconds', 'Task execution duration', ['task_type']),
            'api_response_time': Histogram('web4ai_api_response_time_seconds', 'API response time', ['endpoint']),
            
            # Summaries
            'task_success_rate': Summary('web4ai_task_success_rate', 'Task success rate')
        }
    
    def record_metric(self, metric_name: str, value: float, 
                     timestamp: Optional[datetime] = None, tags: Dict[str, str] = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        metric_data = {
            'value': value,
            'timestamp': timestamp,
            'tags': tags or {}
        }
        
        self.metrics_history[metric_name].append(metric_data)
        
        # Update Prometheus metrics
        self._update_prometheus_metric(metric_name, value, tags or {})
        
        # Cleanup old metrics
        self._cleanup_old_metrics()
    
    def _update_prometheus_metric(self, metric_name: str, value: float, tags: Dict[str, str]):
        """Update Prometheus metrics"""
        if metric_name in self.prometheus_metrics:
            metric = self.prometheus_metrics[metric_name]
            
            if isinstance(metric, Gauge):
                if tags:
                    metric.labels(**tags).set(value)
                else:
                    metric.set(value)
            elif isinstance(metric, Counter):
                if tags:
                    metric.labels(**tags).inc(value)
                else:
                    metric.inc(value)
            elif isinstance(metric, (Histogram, Summary)):
                if tags:
                    metric.labels(**tags).observe(value)
                else:
                    metric.observe(value)
    
    def get_metric_values(self, metric_name: str, 
                         since: Optional[datetime] = None,
                         until: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get metric values within time range"""
        if metric_name not in self.metrics_history:
            return []
        
        values = list(self.metrics_history[metric_name])
        
        if since or until:
            filtered_values = []
            for metric_data in values:
                timestamp = metric_data['timestamp']
                if since and timestamp < since:
                    continue
                if until and timestamp > until:
                    continue
                filtered_values.append(metric_data)
            values = filtered_values
        
        return values
    
    def get_metric_statistics(self, metric_name: str, 
                             since: Optional[datetime] = None) -> Dict[str, float]:
        """Get statistical summary of metric"""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=1)
        
        values = self.get_metric_values(metric_name, since=since)
        if not values:
            return {}
        
        numeric_values = [v['value'] for v in values]
        
        return {
            'count': len(numeric_values),
            'mean': statistics.mean(numeric_values),
            'median': statistics.median(numeric_values),
            'min': min(numeric_values),
            'max': max(numeric_values),
            'std_dev': statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
        }
    
    def _cleanup_old_metrics(self):
        """Remove old metric data beyond retention period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for metric_name, metric_data in self.metrics_history.items():
            # Remove old entries
            while metric_data and metric_data[0]['timestamp'] < cutoff_time:
                metric_data.popleft()

class ThresholdMonitor:
    """Monitor metrics against thresholds and generate alerts"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.thresholds: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
    def add_threshold(self, metric_name: str, 
                     critical_threshold: Optional[float] = None,
                     warning_threshold: Optional[float] = None,
                     comparison: str = "greater",  # greater, less, equal
                     window_minutes: int = 5,
                     min_samples: int = 3):
        """Add threshold monitoring for a metric"""
        self.thresholds[metric_name] = {
            'critical_threshold': critical_threshold,
            'warning_threshold': warning_threshold,
            'comparison': comparison,
            'window_minutes': window_minutes,
            'min_samples': min_samples
        }
        
        logger.info(f"Added threshold monitoring for {metric_name}")
    
    def check_thresholds(self):
        """Check all metrics against their thresholds"""
        current_time = datetime.utcnow()
        
        for metric_name, threshold_config in self.thresholds.items():
            window_start = current_time - timedelta(minutes=threshold_config['window_minutes'])
            
            # Get recent metric values
            values = self.metric_collector.get_metric_values(
                metric_name, since=window_start
            )
            
            if len(values) < threshold_config['min_samples']:
                continue  # Not enough samples
            
            # Calculate average value in window
            avg_value = statistics.mean([v['value'] for v in values])
            
            # Check thresholds
            self._check_metric_threshold(metric_name, avg_value, threshold_config)
    
    def _check_metric_threshold(self, metric_name: str, value: float, 
                               threshold_config: Dict[str, Any]):
        """Check a single metric against its thresholds"""
        comparison = threshold_config['comparison']
        critical_threshold = threshold_config.get('critical_threshold')
        warning_threshold = threshold_config.get('warning_threshold')
        
        # Determine if threshold is breached
        severity = None
        breached_threshold = None
        
        if critical_threshold is not None:
            if self._compare_value(value, critical_threshold, comparison):
                severity = AlertSeverity.CRITICAL
                breached_threshold = critical_threshold
        
        if severity is None and warning_threshold is not None:
            if self._compare_value(value, warning_threshold, comparison):
                severity = AlertSeverity.WARNING
                breached_threshold = warning_threshold
        
        alert_id = f"{metric_name}_threshold"
        
        if severity:
            # Threshold breached - create or update alert
            if alert_id not in self.active_alerts:
                alert = Alert(
                    id=alert_id,
                    title=f"{metric_name} threshold exceeded",
                    description=f"{metric_name} value {value:.2f} {comparison} than threshold {breached_threshold}",
                    severity=severity,
                    status=AlertStatus.ACTIVE,
                    source="threshold_monitor",
                    metric_name=metric_name,
                    metric_value=value,
                    threshold_value=breached_threshold,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.active_alerts[alert_id] = alert
                self._trigger_alert(alert)
            else:
                # Update existing alert
                alert = self.active_alerts[alert_id]
                alert.metric_value = value
                alert.updated_at = datetime.utcnow()
                
                # Escalate if severity increased
                if severity == AlertSeverity.CRITICAL and alert.severity == AlertSeverity.WARNING:
                    alert.severity = severity
                    self._trigger_alert(alert)
        
        else:
            # Threshold not breached - resolve alert if it exists
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                alert.updated_at = datetime.utcnow()
                
                self._trigger_alert(alert)
                del self.active_alerts[alert_id]
    
    def _compare_value(self, value: float, threshold: float, comparison: str) -> bool:
        """Compare value against threshold"""
        if comparison == "greater":
            return value > threshold
        elif comparison == "less":
            return value < threshold
        elif comparison == "equal":
            return abs(value - threshold) < 0.001  # Float comparison tolerance
        else:
            return False
    
    def _trigger_alert(self, alert: Alert):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = datetime.utcnow()

class NotificationManager:
    """Manage multi-channel notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notification_channels = {
            'email': self._send_email_notification,
            'slack': self._send_slack_notification,
            'webhook': self._send_webhook_notification,
            'console': self._send_console_notification
        }
    
    def send_alert_notification(self, alert: Alert):
        """Send alert through configured notification channels"""
        alert_config = self.config.get('alerts', {})
        
        if not alert_config.get('enabled', False):
            return
        
        # Determine which channels to use based on severity
        channels = self._get_channels_for_severity(alert.severity)
        
        for channel in channels:
            if channel in self.notification_channels:
                try:
                    self.notification_channels[channel](alert)
                except Exception as e:
                    logger.error(f"Failed to send {channel} notification: {e}")
    
    def _get_channels_for_severity(self, severity: AlertSeverity) -> List[str]:
        """Get notification channels for alert severity"""
        alert_config = self.config.get('alerts', {})
        
        channels = ['console']  # Always log to console
        
        if severity == AlertSeverity.CRITICAL:
            channels.extend(['email', 'slack', 'webhook'])
        elif severity == AlertSeverity.WARNING:
            channels.extend(['email', 'slack'])
        elif severity == AlertSeverity.INFO:
            channels.append('slack')
        
        # Filter to only enabled channels
        enabled_channels = []
        for channel in channels:
            if alert_config.get(channel, {}).get('enabled', False):
                enabled_channels.append(channel)
        
        return enabled_channels
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        email_config = self.config.get('alerts', {}).get('email', {})
        
        if not email_config.get('enabled', False):
            return
        
        smtp_server = email_config.get('smtp_server')
        smtp_port = email_config.get('smtp_port', 587)
        username = email_config.get('username')
        password = email_config.get('password')
        recipients = email_config.get('recipients', [])
        
        if not all([smtp_server, username, password, recipients]):
            logger.error("Email configuration incomplete")
            return
        
        # Create email message
        msg = MimeMultipart()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Web4AI Alert: {alert.title}"
        
        # Email body
        body = f"""
Web4AI Orchestrator Alert

Title: {alert.title}
Severity: {alert.severity.value.upper()}
Status: {alert.status.value.upper()}
Description: {alert.description}

Metric: {alert.metric_name}
Current Value: {alert.metric_value:.2f}
Threshold: {alert.threshold_value:.2f}

Created: {alert.created_at}
Updated: {alert.updated_at}

Source: {alert.source}

---
This is an automated message from Web4AI Orchestrator.
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent email alert for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        slack_config = self.config.get('alerts', {}).get('slack', {})
        
        if not slack_config.get('enabled', False):
            return
        
        webhook_url = slack_config.get('webhook_url')
        channel = slack_config.get('channel', '#alerts')
        
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return
        
        # Determine color based on severity
        color_map = {
            AlertSeverity.CRITICAL: '#FF0000',  # Red
            AlertSeverity.WARNING: '#FFA500',   # Orange
            AlertSeverity.INFO: '#0000FF',      # Blue
            AlertSeverity.DEBUG: '#808080'      # Gray
        }
        
        # Create Slack message
        message = {
            "channel": channel,
            "username": "Web4AI Orchestrator",
            "icon_emoji": ":warning:",
            "attachments": [{
                "color": color_map.get(alert.severity, '#808080'),
                "title": alert.title,
                "text": alert.description,
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert.severity.value.upper(),
                        "short": True
                    },
                    {
                        "title": "Metric",
                        "value": alert.metric_name,
                        "short": True
                    },
                    {
                        "title": "Current Value",
                        "value": f"{alert.metric_value:.2f}",
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": f"{alert.threshold_value:.2f}",
                        "short": True
                    }
                ],
                "timestamp": alert.created_at.timestamp()
            }]
        }
        
        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
            logger.info(f"Sent Slack alert for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification"""
        webhook_config = self.config.get('alerts', {}).get('webhook', {})
        
        if not webhook_config.get('enabled', False):
            return
        
        webhook_url = webhook_config.get('url')
        if not webhook_url:
            return
        
        # Create webhook payload
        payload = {
            "alert": asdict(alert),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "web4ai_orchestrator"
        }
        
        # Convert datetime objects to strings for JSON serialization
        payload["alert"]["created_at"] = alert.created_at.isoformat()
        payload["alert"]["updated_at"] = alert.updated_at.isoformat()
        if alert.resolved_at:
            payload["alert"]["resolved_at"] = alert.resolved_at.isoformat()
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Sent webhook alert for {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_console_notification(self, alert: Alert):
        """Send console notification (logging)"""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.DEBUG: logging.DEBUG
        }
        
        logger.log(
            log_level.get(alert.severity, logging.INFO),
            f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.description}"
        )

class HealthChecker:
    """Comprehensive health checking for orchestrator components"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.health_checks = {
            'orchestrator_running': self._check_orchestrator_running,
            'nodes_responsive': self._check_nodes_responsive,
            'database_connection': self._check_database_connection,
            'memory_usage': self._check_memory_usage,
            'disk_space': self._check_disk_space,
            'task_processing': self._check_task_processing
        }
        
    def run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks"""
        results = {}
        
        for check_name, check_function in self.health_checks.items():
            try:
                results[check_name] = check_function()
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return results
    
    def _check_orchestrator_running(self) -> Dict[str, Any]:
        """Check if orchestrator is running properly"""
        if self.orchestrator and self.orchestrator.running:
            return {
                'status': 'healthy',
                'message': 'Orchestrator is running',
                'details': {
                    'orchestrator_id': self.orchestrator.orchestrator_id,
                    'uptime': time.time() - self.orchestrator.network_metrics.get('uptime', time.time())
                }
            }
        else:
            return {
                'status': 'unhealthy',
                'message': 'Orchestrator is not running'
            }
    
    def _check_nodes_responsive(self) -> Dict[str, Any]:
        """Check if nodes are responsive"""
        if not self.orchestrator:
            return {'status': 'error', 'message': 'Orchestrator not available'}
        
        active_nodes = [node for node in self.orchestrator.nodes.values() 
                       if node.status.value == 'active']
        
        if not active_nodes:
            return {
                'status': 'warning',
                'message': 'No active nodes available'
            }
        
        # Check recent heartbeats
        current_time = time.time()
        responsive_nodes = 0
        
        for node in active_nodes:
            if current_time - node.last_heartbeat < 120:  # 2 minutes
                responsive_nodes += 1
        
        if responsive_nodes == 0:
            return {
                'status': 'critical',
                'message': 'No nodes are responsive'
            }
        elif responsive_nodes < len(active_nodes):
            return {
                'status': 'warning',
                'message': f'Only {responsive_nodes}/{len(active_nodes)} nodes are responsive'
            }
        else:
            return {
                'status': 'healthy',
                'message': f'All {responsive_nodes} nodes are responsive'
            }
    
    def _check_database_connection(self) -> Dict[str, Any]:
        """Check database connection"""
        # This would check Redis/MongoDB/PostgreSQL connection
        # Implementation depends on your storage backend
        return {
            'status': 'healthy',
            'message': 'Database connection is healthy'
        }
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        import psutil
        
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        if usage_percent > 90:
            status = 'critical'
        elif usage_percent > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'message': f'Memory usage: {usage_percent:.1f}%',
            'details': {
                'used_gb': memory.used / (1024**3),
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3)
            }
        }
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space"""
        import psutil
        
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        if usage_percent > 90:
            status = 'critical'
        elif usage_percent > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'message': f'Disk usage: {usage_percent:.1f}%',
            'details': {
                'used_gb': disk.used / (1024**3),
                'total_gb': disk.total / (1024**3),
                'free_gb': disk.free / (1024**3)
            }
        }
    
    def _check_task_processing(self) -> Dict[str, Any]:
        """Check task processing health"""
        if not self.orchestrator:
            return {'status': 'error', 'message': 'Orchestrator not available'}
        
        pending_count = len(self.orchestrator.pending_tasks)
        active_count = len(self.orchestrator.active_tasks)
        
        if pending_count > 100:
            status = 'warning'
            message = f'High number of pending tasks: {pending_count}'
        elif active_count == 0 and pending_count > 0:
            status = 'warning'
            message = f'Tasks pending but none active: {pending_count} pending'
        else:
            status = 'healthy'
            message = f'Task processing normal: {pending_count} pending, {active_count} active'
        
        return {
            'status': status,
            'message': message,
            'details': {
                'pending_tasks': pending_count,
                'active_tasks': active_count,
                'completed_tasks': len(self.orchestrator.completed_tasks),
                'failed_tasks': len(self.orchestrator.failed_tasks)
            }
        }

class MonitoringManager:
    """Main monitoring manager that coordinates all monitoring components"""
    
    def __init__(self, config: Dict[str, Any], orchestrator=None):
        self.config = config
        self.orchestrator = orchestrator
        
        # Initialize components
        self.metric_collector = MetricCollector(
            retention_hours=config.get('performance', {}).get('metrics_retention_hours', 24)
        )
        self.threshold_monitor = ThresholdMonitor(self.metric_collector)
        self.notification_manager = NotificationManager(config)
        self.health_checker = HealthChecker(orchestrator)
        
        # Setup alert callback
        self.threshold_monitor.add_alert_callback(
            self.notification_manager.send_alert_notification
        )
        
        # Setup default thresholds
        self._setup_default_thresholds()
        
        # Background monitoring
        self.monitoring_thread = None
        self.running = False
    
    def _setup_default_thresholds(self):
        """Setup default monitoring thresholds"""
        thresholds_config = self.config.get('alerts', {}).get('thresholds', {})
        
        # Network utilization
        self.threshold_monitor.add_threshold(
            'network_utilization',
            critical_threshold=thresholds_config.get('high_utilization', 0.9),
            warning_threshold=thresholds_config.get('medium_utilization', 0.8),
            comparison='greater'
        )
        
        # Node failure rate
        self.threshold_monitor.add_threshold(
            'node_failure_rate',
            critical_threshold=thresholds_config.get('node_failure_count', 3),
            warning_threshold=2,
            comparison='greater'
        )
        
        # Task success rate
        self.threshold_monitor.add_threshold(
            'task_success_rate',
            critical_threshold=thresholds_config.get('low_success_rate', 0.8),
            warning_threshold=0.9,
            comparison='less'
        )
        
        # Response time
        self.threshold_monitor.add_threshold(
            'average_response_time',
            critical_threshold=thresholds_config.get('high_response_time', 5000),
            warning_threshold=3000,
            comparison='greater'
        )
    
    def start_monitoring(self):
        """Start background monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Monitoring manager started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        logger.info("Monitoring manager stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Collect current metrics
                self._collect_orchestrator_metrics()
                
                # Check thresholds
                self.threshold_monitor.check_thresholds()
                
                # Wait before next iteration
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)
    
    def _collect_orchestrator_metrics(self):
        """Collect metrics from orchestrator"""
        if not self.orchestrator:
            return
        
        current_time = datetime.utcnow()
        
        # Network metrics
        network_metrics = self.orchestrator.network_metrics
        
        self.metric_collector.record_metric(
            'network_utilization',
            network_metrics.get('network_utilization', 0),
            current_time
        )
        
        self.metric_collector.record_metric(
            'active_nodes',
            network_metrics.get('active_nodes', 0),
            current_time
        )
        
        self.metric_collector.record_metric(
            'tasks_completed',
            network_metrics.get('tasks_completed', 0),
            current_time
        )
        
        self.metric_collector.record_metric(
            'tasks_failed',
            network_metrics.get('tasks_failed', 0),
            current_time
        )
        
        # Calculate success rate
        total_tasks = network_metrics.get('tasks_completed', 0) + network_metrics.get('tasks_failed', 0)
        if total_tasks > 0:
            success_rate = network_metrics.get('tasks_completed', 0) / total_tasks
            self.metric_collector.record_metric('task_success_rate', success_rate, current_time)
        
        # Response time
        self.metric_collector.record_metric(
            'average_response_time',
            network_metrics.get('average_response_time', 0),
            current_time
        )
        
        # Node-specific metrics
        for node_id, node in self.orchestrator.nodes.items():
            node_tags = {'node_id': node_id}
            
            self.metric_collector.record_metric(
                'node_cpu_usage',
                node.cpu_usage,
                current_time,
                node_tags
            )
            
            self.metric_collector.record_metric(
                'node_memory_usage',
                node.memory_usage,
                current_time,
                node_tags
            )
            
            self.metric_collector.record_metric(
                'node_load_score',
                node.load_score,
                current_time,
                node_tags
            )
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        
        dashboard_data = {
            'timestamp': current_time.isoformat(),
            'metrics': {},
            'alerts': {
                'active': [asdict(alert) for alert in self.threshold_monitor.active_alerts.values()],
                'count_by_severity': defaultdict(int)
            },
            'health_checks': self.health_checker.run_health_checks()
        }
        
        # Get metric statistics
        for metric_name in ['network_utilization', 'active_nodes', 'task_success_rate', 'average_response_time']:
            stats = self.metric_collector.get_metric_statistics(metric_name, since=one_hour_ago)
            values = self.metric_collector.get_metric_values(metric_name, since=one_hour_ago)
            
            dashboard_data['metrics'][metric_name] = {
                'statistics': stats,
                'recent_values': [
                    {
                        'timestamp': v['timestamp'].isoformat(),
                        'value': v['value']
                    } for v in values[-20:]  # Last 20 values
                ]
            }
        
        # Count alerts by severity
        for alert in self.threshold_monitor.active_alerts.values():
            dashboard_data['alerts']['count_by_severity'][alert.severity.value] += 1
        
        return dashboard_data

# Example usage in orchestrator
def setup_monitoring(orchestrator, config):
    """Setup monitoring for orchestrator"""
    monitoring_manager = MonitoringManager(config, orchestrator)
    monitoring_manager.start_monitoring()
    
    # Add custom metrics collection
    def collect_custom_metrics():
        # Example: collect task queue depth
        monitoring_manager.metric_collector.record_metric(
            'pending_tasks_count',
            len(orchestrator.pending_tasks)
        )
        
        # Example: collect node failure events
        failed_nodes = [node for node in orchestrator.nodes.values() 
                       if node.status.value == 'offline']
        monitoring_manager.metric_collector.record_metric(
            'failed_nodes_count',
            len(failed_nodes)
        )
    
    # Schedule custom metrics collection
    import threading
    def metrics_timer():
        while True:
            time.sleep(30)  # Collect every 30 seconds
            try:
                collect_custom_metrics()
            except Exception as e:
                logger.error(f"Custom metrics collection error: {e}")
    
    metrics_thread = threading.Thread(target=metrics_timer, daemon=True)
    metrics_thread.start()
    
    return monitoring_manager