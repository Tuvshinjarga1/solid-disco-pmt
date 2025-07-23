"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from bot import process_fastapi_request, handle_test_message, handle_teams_message
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
    
    if Config.DEVELOPMENT_MODE:
        # Development mode - Teams activity ойлгож, OpenAI шууд ашиглах
        try:
            body = await request.json()
            
            # Teams activity format шалгах
            if body.get("type") == "message" and body.get("text"):
                user_message = body.get("text", "")
                
                # OpenAI-аар хариулж, Teams reply илгээх
                result = await handle_teams_message(user_message, body)
                
                return JSONResponse(content={
                    "status": "processed",
                    "mode": "development_teams_direct",
                    "user_message": user_message,
                    "bot_response": result.get("bot_response"),
                    "reply_sent_to_teams": result.get("reply_sent", False),
                    "teams_context": result.get("teams_context", {})
                }, status_code=200)
            
            else:
                # Teams system messages (member added, etc.)
                return JSONResponse(content={
                    "status": "ok", 
                    "mode": "development_teams_system",
                    "activity_type": body.get("type", "unknown")
                }, status_code=200)
                
        except Exception as e:
            print(f"Development Teams mode error: {e}")
            return JSONResponse(content={
                "status": "error", 
                "error": str(e)
            }, status_code=500)
    
    else:
        # Production mode - Teams AI framework ашиглах
        res = await process_fastapi_request(request)
        
        if res is not None:
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
        "development_mode": Config.DEVELOPMENT_MODE,
        "teams_reply_enabled": Config.TEAMS_REPLY_ENABLED,
        "bot_credentials_configured": bool(Config.APP_ID and Config.APP_PASSWORD),
        "public_url": f"https://{railway_url}" if railway_url != "unknown" else f"http://localhost:{port}",
        "endpoints": {
            "teams_webhook": "/api/messages" + (" (development mode - direct OpenAI)" if Config.DEVELOPMENT_MODE else " (production mode - Teams AI framework)"),
            "test_chat": "/api/test",
            "docs": "/docs"
        },
        "features": {
            "openai_chat": "enabled",
            "teams_reply": "enabled" if Config.TEAMS_REPLY_ENABLED else "disabled (console only)",
            "authentication": "enabled" if not Config.DEVELOPMENT_MODE else "disabled (dev mode)"
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
    print(f"🧪 Development Mode: {Config.DEVELOPMENT_MODE}")
    print(f"💬 Teams Reply: {'Enabled' if Config.TEAMS_REPLY_ENABLED else 'Disabled (console only)'}")
    
    if Config.DEVELOPMENT_MODE:
        print("🔧 Teams messages will use direct OpenAI (bypass authentication)")
    else:
        print("🔒 Teams messages will use full Teams AI framework")
        
    if not Config.TEAMS_REPLY_ENABLED:
        print("ℹ️ Teams client дээр bot хариу харагдахгүй - зөвхөн console лог")
        print("💡 Teams reply идэвхжүүлэх: TEAMS_REPLY_ENABLED=true, BOT_ID/BOT_PASSWORD тохируулах")
    
    # Railway дээр public URL харуулах
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_url:
        print(f"🔗 Public URL: https://{railway_url}")
        print(f"🧪 Test endpoint: https://{railway_url}/api/test")
        print(f"🤖 Teams webhook: https://{railway_url}/api/messages")
    else:
        print(f"🔗 Local URL: http://localhost:{port}")
        print(f"🧪 Test endpoint: http://localhost:{port}/api/test")
        print(f"🤖 Teams webhook: http://localhost:{port}/api/messages")
    
    # FastAPI app-г uvicorn ашиглан ажиллуулах
    uvicorn.run(
        "app:app",
        host="0.0.0.0",  # Railway болон бусад cloud platforms-д ажиллахын тулд
        port=port,
        reload=False,  # Production-д reload идэвхгүй
        log_level="info",
        access_log=True
    )