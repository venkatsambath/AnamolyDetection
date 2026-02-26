"""
FastAPI application — mounts all route groups and serves the frontend SPA.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import anomalies, metrics, model, reports

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app = FastAPI(
    title="HDFS Namenode Anomaly Detector",
    description="Real-time anomaly detection for HDFS Namenode JMX metrics using an LSTM Autoencoder.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routes ---
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(anomalies.router, prefix="/api", tags=["Anomalies"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(model.router, prefix="/api", tags=["Model"])

# --- Serve frontend static assets ---
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
