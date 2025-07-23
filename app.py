"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
import os
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse

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
    return {
        "status": "healthy", 
        "message": "Teams AI Bot is running",
        "links": {
            "health_json": "/health",
            "health_html": "/health-html",
            "api_docs": "/docs",
            "test_endpoint": "/api/test"
        }
    }

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

@app.get("/health-html", response_class=HTMLResponse)
async def health_check_html():
    """HTML хэлбэрээр health check харуулах"""
    # Railway deployment info нэмэх
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "unknown")
    port = os.environ.get("PORT", Config.PORT)
    
    # Health мэдээлэл цуглуулах
    environment = "production" if railway_url != "unknown" else "development"
    public_url = f"https://{railway_url}" if railway_url != "unknown" else f"http://localhost:{port}"
    bot_configured = bool(Config.APP_ID and Config.APP_PASSWORD)
    
    # HTML template
    html_content = f"""
    <!DOCTYPE html>
    <html lang="mn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Teams AI Bot - Health Status</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .status-badge {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 8px 20px;
                border-radius: 25px;
                margin-top: 10px;
                font-size: 1.1em;
            }}
            .content {{
                padding: 30px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .info-card {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                border-left: 4px solid #4CAF50;
            }}
            .info-card h3 {{
                margin: 0 0 15px 0;
                color: #2c3e50;
                font-size: 1.3em;
            }}
            .info-item {{
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .info-item:last-child {{
                border-bottom: none;
            }}
            .label {{
                font-weight: 600;
                color: #6c757d;
            }}
            .value {{
                color: #2c3e50;
            }}
            .status-enabled {{
                color: #28a745;
                font-weight: bold;
            }}
            .status-disabled {{
                color: #dc3545;
                font-weight: bold;
            }}
            .status-warning {{
                color: #ffc107;
                font-weight: bold;
            }}
            .endpoints {{
                background: #e3f2fd;
                border-radius: 10px;
                padding: 20px;
                margin-top: 20px;
            }}
            .endpoints h3 {{
                margin: 0 0 15px 0;
                color: #1976d2;
            }}
            .endpoint-link {{
                display: block;
                background: white;
                padding: 10px 15px;
                margin: 8px 0;
                border-radius: 5px;
                text-decoration: none;
                color: #1976d2;
                border: 1px solid #e3f2fd;
                transition: all 0.3s ease;
            }}
            .endpoint-link:hover {{
                background: #1976d2;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .refresh-btn {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1.1em;
                transition: all 0.3s ease;
                margin-top: 20px;
                display: block;
                margin-left: auto;
                margin-right: auto;
            }}
            .refresh-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }}
            .timestamp {{
                text-align: center;
                color: #6c757d;
                margin-top: 20px;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Teams AI Bot</h1>
                <div class="status-badge">✅ Healthy & Running</div>
            </div>
            
            <div class="content">
                <div class="info-grid">
                    <div class="info-card">
                        <h3>🔧 System Information</h3>
                        <div class="info-item">
                            <span class="label">Service:</span>
                            <span class="value">Teams AI Bot</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Framework:</span>
                            <span class="value">FastAPI</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Port:</span>
                            <span class="value">{port}</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Environment:</span>
                            <span class="value">{environment.title()}</span>
                        </div>
                    </div>
                    
                    <div class="info-card">
                        <h3>⚙️ Configuration</h3>
                        <div class="info-item">
                            <span class="label">Development Mode:</span>
                            <span class="value {'status-warning' if Config.DEVELOPMENT_MODE else 'status-enabled'}">
                                {'Enabled' if Config.DEVELOPMENT_MODE else 'Disabled'}
                            </span>
                        </div>
                        <div class="info-item">
                            <span class="label">Teams Reply:</span>
                            <span class="value {'status-enabled' if Config.TEAMS_REPLY_ENABLED else 'status-disabled'}">
                                {'Enabled' if Config.TEAMS_REPLY_ENABLED else 'Disabled'}
                            </span>
                        </div>
                        <div class="info-item">
                            <span class="label">Bot Credentials:</span>
                            <span class="value {'status-enabled' if bot_configured else 'status-disabled'}">
                                {'Configured' if bot_configured else 'Not Configured'}
                            </span>
                        </div>
                    </div>
                    
                    <div class="info-card">
                        <h3>🚀 Features</h3>
                        <div class="info-item">
                            <span class="label">OpenAI Chat:</span>
                            <span class="value status-enabled">Enabled</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Authentication:</span>
                            <span class="value {'status-disabled' if Config.DEVELOPMENT_MODE else 'status-enabled'}">
                                {'Disabled (Dev Mode)' if Config.DEVELOPMENT_MODE else 'Enabled'}
                            </span>
                        </div>
                        <div class="info-item">
                            <span class="label">Teams Integration:</span>
                            <span class="value {'status-warning' if Config.DEVELOPMENT_MODE else 'status-enabled'}">
                                {'Direct OpenAI' if Config.DEVELOPMENT_MODE else 'Full Teams AI'}
                            </span>
                        </div>
                    </div>
                    
                    <div class="info-card">
                        <h3>🌐 Network</h3>
                        <div class="info-item">
                            <span class="label">Public URL:</span>
                            <span class="value">{public_url}</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Railway Domain:</span>
                            <span class="value">{railway_url if railway_url != 'unknown' else 'Local Development'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="endpoints">
                    <h3>🔗 Available Endpoints</h3>
                    <a href="/api/messages" class="endpoint-link">
                        <strong>/api/messages</strong> - Teams Webhook 
                        ({('Development Mode - Direct OpenAI' if Config.DEVELOPMENT_MODE else 'Production Mode - Teams AI Framework')})
                    </a>
                    <a href="/api/test" class="endpoint-link">
                        <strong>/api/test</strong> - Test Chat (POST request)
                    </a>
                    <a href="/health" class="endpoint-link">
                        <strong>/health</strong> - Health Check (JSON)
                    </a>
                    <a href="/docs" class="endpoint-link">
                        <strong>/docs</strong> - API Documentation (Swagger UI)
                    </a>
                    <a href="/redoc" class="endpoint-link">
                        <strong>/redoc</strong> - API Documentation (ReDoc)
                    </a>
                </div>
                
                <button class="refresh-btn" onclick="window.location.reload()">
                    🔄 Refresh Status
                </button>
                
                <div class="timestamp">
                    Last updated: <span id="timestamp"></span>
                </div>
            </div>
        </div>
        
        <script>
            // Current timestamp харуулах
            document.getElementById('timestamp').textContent = new Date().toLocaleString('mn-MN');
            
            // Auto refresh every 30 seconds
            setTimeout(() => {{
                window.location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

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