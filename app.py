"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from bot import process_fastapi_request
from config import Config

# FastAPI app үүсгэх
app = FastAPI(
    title="Teams AI Bot",
    description="Microsoft Teams AI Bot using FastAPI",
    version="1.0.0",
    docs_url="/docs",  # API documentation
    redoc_url="/redoc"  # Alternative API docs
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Teams AI Bot is running"}

@app.post("/api/messages")
async def on_messages(request: Request) -> Response:
    """Teams bot messages endpoint"""
    # FastAPI Request-г Teams AI bot рүү дамжуулах
    res = await process_fastapi_request(request)
    
    if res is not None:
        # Bot-оос Response ирвэл success status буцаах
        return JSONResponse(content={"status": "processed"}, status_code=200)
    
    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.get("/health")
async def health_check():
    """Detailed health check for monitoring"""
    return {
        "status": "healthy",
        "service": "teams-ai-bot",
        "port": Config.PORT,
        "framework": "FastAPI"
    }

# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    # FastAPI app-г uvicorn ашиглан ажиллуулах
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # Docker container-д ажиллахын тулд 0.0.0.0
        port=Config.PORT,
        reload=False,  # Production-д reload идэвхгүй
        log_level="info",
        access_log=True
    )