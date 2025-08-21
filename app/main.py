from fastapi import FastAPI
from prometheus_client import start_http_server, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import threading

app = FastAPI(
    title="SECURESNAP DevSecOps API",
    description="A secure FastAPI application with Prometheus metrics",
    version="1.0.0"
)

# Prometheus metrics
REQUEST_COUNT = Counter("app_requests_total", "Total number of requests", ["endpoint"])

@app.on_event("startup")
async def startup_event():
    # Start Prometheus metrics server on port 8001
    start_http_server(8001)
    print("✅ Prometheus metrics server started on port 8001")

@app.get("/")
def read_root():
    REQUEST_COUNT.labels(endpoint="root").inc()
    return {"message": "Hello, SECURESNAP DevSecOps!"}

@app.get("/health")
def health_check():
    REQUEST_COUNT.labels(endpoint="health").inc()
    return {"status": "healthy", "service": "securesnap"}

@app.get("/info")
def get_info():
    REQUEST_COUNT.labels(endpoint="info").inc()
    return {
        "service": "SECURESNAP",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/", "/health", "/info", "/metrics"],
        "metrics_endpoint": "/metrics",
        "prometheus_port": 8001
    }

@app.get("/metrics")
def get_metrics():
    REQUEST_COUNT.labels(endpoint="metrics").inc()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/debug")
def debug_info():
    REQUEST_COUNT.labels(endpoint="debug").inc()
    import os
    return {
        "environment": os.environ.get("ENV", "development"),
        "python_version": "3.11",
        "working_directory": os.getcwd(),
        "routes_available": True
    }
