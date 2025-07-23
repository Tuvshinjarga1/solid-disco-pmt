"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from bot import process_fastapi_request, handle_test_message
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
    """Teams bot messages endpoint - Microsoft Bot Framework"""
    # FastAPI Request-г Teams AI bot рүү дамжуулах
    res = await process_fastapi_request(request)
    
    if res is not None:
        # Bot-оос Response ирвэл success status буцаах
        return JSONResponse(content={"status": "processed"}, status_code=200)
    
    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.post("/api/test")
async def test_chat(request: Request) -> Response:
    """Development test endpoint - Authentication шаардлагагүй"""
    try:
        # Request body уншиж авах
        body = await request.json()
        user_message = body.get("message", "")
        
        if not user_message:
            return JSONResponse(
                content={"error": "Message field шаардлагатай"}, 
                status_code=400
            )
        
        # Bot response авах (authentication-гүйгээр)
        bot_response = await handle_test_message(user_message)
        
        return JSONResponse(content={
            "status": "success",
            "user_message": user_message,
            "bot_response": bot_response,
            "note": "Development test mode - authentication bypass"
        })
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Test mode error: {str(e)}"}, 
            status_code=500
        )

@app.get("/health")
async def health_check():
    """Detailed health check for monitoring"""
    # Railway deployment info нэмэх
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "unknown")
    port = os.environ.get("PORT", Config.PORT)
    
    return {
        "status": "healthy",
        "service": "teams-ai-bot",
        "port": port,
        "framework": "FastAPI",
        "environment": "production" if railway_url != "unknown" else "development",
        "public_url": f"https://{railway_url}" if railway_url != "unknown" else f"http://localhost:{port}",
        "endpoints": {
            "teams_webhook": "/api/messages",
            "test_chat": "/api/test",
            "docs": "/docs"
        }
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
    # Railway платформын PORT environment variable ашиглах
    port = int(os.environ.get("PORT", Config.PORT))
    
    print(f"🚀 Starting Teams AI Bot...")
    print(f"📍 Port: {port}")
    print(f"🌐 Host: 0.0.0.0 (Railway compatible)")
    
    # Railway дээр public URL харуулах
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_url:
        print(f"🔗 Public URL: https://{railway_url}")
        print(f"🧪 Test endpoint: https://{railway_url}/api/test")
    else:
        print(f"🔗 Local URL: http://localhost:{port}")
        print(f"🧪 Test endpoint: http://localhost:{port}/api/test")
    
    # FastAPI app-г uvicorn ашиглан ажиллуулах
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # Railway болон бусад cloud platforms-д ажиллахын тулд
        port=port,
        reload=False,  # Production-д reload идэвхгүй
        log_level="info",
        access_log=True
    )