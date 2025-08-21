from fastapi import FastAPI
from prometheus_client import start_http_server, Counter
import threading

app = FastAPI()

REQUEST_COUNT = Counter("app_requests_total", "Total number of requests")

@app.get("/")
def read_root():
    REQUEST_COUNT.inc()
    return {"message": "Hello, SECURESNAP DevSecOps!"}

@app.get("/health")
def health_check():
    REQUEST_COUNT.inc()
    return {"status": "healthy"}

# Start Prometheus metrics server
def start_metrics_server():
    start_http_server(8001)

if __name__ == "__main__":
    # Start metrics server in background
    metrics_thread = threading.Thread(target=start_metrics_server)
    metrics_thread.daemon = True
    metrics_thread.start()
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
