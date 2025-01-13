import app
from app.logging import Ansi, log
from prometheus_client import Counter, Gauge, Histogram, start_http_server

METRICS = {
    "ex_submitted_scores": Counter("ex_submitted_scores", "Total number of scores submitted"),
    "ex_submitted_scores_best": Counter("ex_submitted_scores_best", "Total number of best scores submitted"),
    "ex_leaderboards_served": Counter("ex_leaderboards_served", "Total number of leaderboards served"),
    "ex_registrations": Counter("ex_registrations", "Total number of user registrations"),
    "ex_online_players": Counter("ex_online_players", "Total number of players currently online"),
    "ex_login_time": Histogram("ex_login_time", "Login time latency in seconds"),
    "ex_first_place_webhook": Counter("ex_first_place_webhook", "First place webhooks send"),
    "ex_chat_messages": Counter("ex_chat_messages", "Total number of chat messages sent"),
    "ex_logins": Counter("ex_logins", "Total number of logins"),
}

enabled = app.settings.ENABLE_PROMETHEUS

def start_metrics_server():
    """Starts the Prometheus metrics server if enabled."""
    if not enabled:
        return

    log(
        f"Starting metrics server on 127.0.0.1:{app.settings.PROMETHEUS_PORT}",
        Ansi.LYELLOW,
    )

    start_http_server(app.settings.PROMETHEUS_PORT)

def increment(metric: str):
    """Increments the specified metric by 1."""
    if not enabled:
        return

    metric_object = METRICS.get(metric)
    if metric_object is None:
        raise ValueError(f"Invalid metric name: {metric}")

    metric_object.inc()

def decrement(metric: str):
    """Decrements the specified metric by 1."""
    if not enabled:
        return

    metric_object = METRICS.get(metric)
    if metric_object is None:
        raise ValueError(f"Invalid metric name: {metric}")

    metric_object.dec()

def histrogram(metric: str, value: float):
    """Records a value for the specified histogram metric."""
    if not enabled:
        return

    metric_object = METRICS.get(metric)
    if metric_object is None:
        raise ValueError(f"Invalid metric name: {metric}")

    metric_object.observe(value)