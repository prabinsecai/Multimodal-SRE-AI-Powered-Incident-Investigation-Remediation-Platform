from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ServiceState:
    name: str
    version: str = "v1.8.3"
    healthy: bool = True
    error_rate: float = 0.002
    latency_ms: float = 85.0
    cpu_percent: float = 38.0
    memory_percent: float = 45.0
    replicas: int = 3
    active_connections: int = 14
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class MockKubernetesProvider:
    """
    Simulates Kubernetes workload management, rollout deployments,
    pod health probing, and remediation actions.
    """
    def __init__(self):
        self.services: dict[str, ServiceState] = {
            "payment-api": ServiceState(name="payment-api", version="v1.8.3", healthy=True, error_rate=0.002, latency_ms=92.0),
            "order-api": ServiceState(name="order-api", version="v2.1.0", healthy=True, error_rate=0.001, latency_ms=45.0),
            "auth-api": ServiceState(name="auth-api", version="v3.0.4", healthy=True, error_rate=0.0005, latency_ms=28.0),
            "notification-worker": ServiceState(name="notification-worker", version="v1.4.0", healthy=True, error_rate=0.001, latency_ms=110.0),
            "inventory-service": ServiceState(name="inventory-service", version="v1.2.9", healthy=True, error_rate=0.003, latency_ms=60.0),
        }

    def get_service(self, name: str) -> ServiceState:
        if name not in self.services:
            self.services[name] = ServiceState(name=name)
        return self.services[name]

    def rollback_service(self, name: str, version: str = "v1.8.2") -> dict[str, Any]:
        svc = self.get_service(name)
        svc.version = version
        svc.healthy = True
        svc.error_rate = 0.002
        svc.latency_ms = 85.0
        svc.active_connections = 12
        svc.cpu_percent = 35.0
        svc.memory_percent = 40.0
        svc.last_updated = datetime.now(timezone.utc)
        return {
            "mode": "simulation",
            "action": "rollback_deployment",
            "service": name,
            "target_version": version,
            "status": "rolled_back",
            "message": f"Successfully rolled back {name} deployment to stable image {version}. Traffic shifted 100%."
        }

    def scale_service(self, name: str, replicas: int = 5) -> dict[str, Any]:
        svc = self.get_service(name)
        svc.replicas = replicas
        svc.cpu_percent = max(20.0, svc.cpu_percent / 2)
        svc.healthy = True
        svc.last_updated = datetime.now(timezone.utc)
        return {
            "mode": "simulation",
            "action": "scale_service",
            "service": name,
            "replicas": replicas,
            "status": "scaled",
            "message": f"Scaled {name} deployment to {replicas} replicas."
        }

    def restart_service(self, name: str) -> dict[str, Any]:
        svc = self.get_service(name)
        svc.healthy = True
        svc.error_rate = 0.001
        svc.memory_percent = 35.0
        svc.active_connections = 8
        svc.last_updated = datetime.now(timezone.utc)
        return {
            "mode": "simulation",
            "action": "restart_service",
            "service": name,
            "status": "restarted",
            "message": f"Restarted pod replicas for {name}. Connection pools and heap cleared."
        }

    def flush_connections(self, name: str) -> dict[str, Any]:
        svc = self.get_service(name)
        svc.active_connections = 8
        svc.error_rate = 0.001
        svc.latency_ms = 75.0
        svc.last_updated = datetime.now(timezone.utc)
        return {
            "mode": "simulation",
            "action": "flush_connections",
            "service": name,
            "status": "flushed",
            "message": f"Flushed active and leaked connection pool handles for {name}."
        }

    def health(self, name: str) -> dict[str, Any]:
        svc = self.get_service(name)
        return {
            "service": svc.name,
            "version": svc.version,
            "healthy": svc.healthy,
            "error_rate": svc.error_rate,
            "latency_ms": svc.latency_ms,
            "cpu_percent": svc.cpu_percent,
            "memory_percent": svc.memory_percent,
            "replicas": svc.replicas,
            "active_connections": svc.active_connections,
            "last_updated": svc.last_updated.isoformat()
        }
