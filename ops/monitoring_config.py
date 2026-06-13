# Ops Configuration: Monitoring
# Centralized monitoring configuration for the WhatsApp Seller Bot

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AlertThreshold:
    """Alert threshold configuration."""
    metric: str
    operator: str  # gt, lt, eq, gte, lte
    value: float
    duration_seconds: int = 60
    severity: str = "warning"  # warning, critical


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prometheus_retention_days: int = 15
    prometheus_scrape_interval: str = "15s"
    
    # Grafana
    grafana_enabled: bool = True
    grafana_port: int = 3001
    grafana_admin_user: str = "admin"
    grafana_admin_password: str = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
    
    # Alert endpoints
    slack_webhook_url: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    email_smtp_host: Optional[str] = os.getenv("SMTP_HOST")
    email_smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_from: Optional[str] = os.getenv("ALERT_EMAIL_FROM")
    email_to: Optional[str] = os.getenv("ALERT_EMAIL_TO")
    
    # Default alert thresholds
    @property
    def default_thresholds(self) -> List[AlertThreshold]:
        return [
            # API latency
            AlertThreshold(
                metric="api_request_latency_seconds",
                operator="gt",
                value=2.0,
                duration_seconds=120,
                severity="warning"
            ),
            AlertThreshold(
                metric="api_request_latency_seconds",
                operator="gt",
                value=5.0,
                duration_seconds=60,
                severity="critical"
            ),
            # Error rate
            AlertThreshold(
                metric="http_requests_total{status=~'5..'}",
                operator="gt",
                value=10,
                duration_seconds=300,
                severity="warning"
            ),
            AlertThreshold(
                metric="http_requests_total{status=~'5..'}",
                operator="gt",
                value=50,
                duration_seconds=60,
                severity="critical"
            ),
            # Memory usage
            AlertThreshold(
                metric="process_resident_memory_bytes",
                operator="gt",
                value=500 * 1024 * 1024,  # 500MB
                duration_seconds=300,
                severity="warning"
            ),
            # Redis connection
            AlertThreshold(
                metric="redis_connected_clients",
                operator="lt",
                value=1,
                duration_seconds=60,
                severity="critical"
            ),
            # LLM cost
            AlertThreshold(
                metric="llm_cost_usd_total",
                operator="gt",
                value=10.0,  # Daily cost threshold
                duration_seconds=86400,
                severity="warning"
            ),
        ]


# Prometheus scrape targets configuration
SCRAPE_TARGETS = {
    "backend": {
        "job_name": "whatsapp-backend",
        "static_configs": [
            {"targets": ["backend:8000"]}
        ],
        "metrics_path": "/metrics",
        "scrape_interval": "15s"
    },
    "redis": {
        "job_name": "redis",
        "static_configs": [
            {"targets": ["redis:6379"]}
        ],
        "scrape_interval": "30s"
    },
    "node_exporter": {
        "job_name": "node",
        "static_configs": [
            {"targets": ["node-exporter:9100"]}
        ],
        "scrape_interval": "30s"
    },
    "cadvisor": {
        "job_name": "cadvisor",
        "static_configs": [
            {"targets": ["cadvisor:8080"]}
        ],
        "scrape_interval": "30s"
    }
}


# Grafana dashboard configurations
GRAFANA_DASHBOARDS = {
    "main": {
        "uid": "whatsapp-bot-main",
        "title": "WhatsApp Bot - Main Dashboard",
        "panels": [
            "api_requests_per_second",
            "api_latency_p95",
            "error_rate",
            "active_conversations",
            "orders_per_hour",
            "llm_tokens_used",
            "llm_cost_today"
        ]
    },
    "performance": {
        "uid": "whatsapp-bot-perf",
        "title": "WhatsApp Bot - Performance",
        "panels": [
            "cpu_usage",
            "memory_usage",
            "disk_io",
            "network_io",
            "container_stats"
        ]
    },
    "business": {
        "uid": "whatsapp-bot-biz",
        "title": "WhatsApp Bot - Business Metrics",
        "panels": [
            "daily_orders",
            "revenue_today",
            "cart_abandonment_rate",
            "popular_products",
            "customer_satisfaction"
        ]
    }
}


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration instance."""
    return MonitoringConfig()


def generate_prometheus_config() -> dict:
    """Generate Prometheus configuration."""
    config = get_monitoring_config()
    
    return {
        "global": {
            "scrape_interval": config.prometheus_scrape_interval,
            "evaluation_interval": "15s"
        },
        "alerting": {
            "alertmanagers": [
                {
                    "static_configs": [
                        {"targets": ["alertmanager:9093"]}
                    ]
                }
            ]
        },
        "rule_files": [
            "/etc/prometheus/rules/*.yml"
        ],
        "scrape_configs": list(SCRAPE_TARGETS.values())
    }
