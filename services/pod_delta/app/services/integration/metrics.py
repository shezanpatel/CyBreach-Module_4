"""Prometheus metrics for Kafka consumption, lag, errors, and WebSockets."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

EVENTS_CONSUMED = Counter(
    "pod_delta_events_consumed_total",
    "Kafka events consumed",
    ["topic"],
)
EVENTS_PUBLISHED = Counter(
    "pod_delta_events_published_total",
    "Kafka events published",
    ["topic"],
)
EVENTS_ERRORS = Counter(
    "pod_delta_events_errors_total",
    "Kafka processing errors",
    ["topic", "reason"],
)
EVENTS_DLT = Counter(
    "pod_delta_events_dlt_total",
    "Events sent to dead-letter topics",
    ["topic"],
)
CONSUMER_LAG = Gauge(
    "pod_delta_kafka_consumer_lag",
    "Approximate consumer lag",
    ["topic", "partition"],
)
PROCESS_SECONDS = Histogram(
    "pod_delta_event_process_seconds",
    "Event handler duration",
    ["topic"],
)
WS_CONNECTIONS = Gauge(
    "pod_delta_websocket_connections",
    "Active local WebSocket connections",
)
RATE_LIMITED = Counter(
    "pod_delta_rate_limited_total",
    "Notifications blocked by rate limiter",
    ["event_type"],
)


def metrics_output() -> bytes:
    return generate_latest()
