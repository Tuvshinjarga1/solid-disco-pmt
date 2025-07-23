import os
import sys
import json
import traceback
from dataclasses import asdict
import aiohttp

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, ApplicationOptions, TeamsAdapter
from teams.ai import AIOptions
from teams.ai.models import AzureOpenAIModelOptions, OpenAIModel, OpenAIModelOptions
from teams.ai.planners import ActionPlanner, ActionPlannerOptions
from teams.ai.prompts import PromptManager, PromptManagerOptions
from teams.state import TurnState
from teams.feedback_loop_data import FeedbackLoopData

from config import Config

config = Config()

# Bot Framework access token кэш
_bot_access_token = None
_token_expires_at = 0

# Microsoft Bot Framework access token авах
async def get_bot_access_token():
    """Microsoft Bot Framework access token авах"""
    global _bot_access_token, _token_expires_at
    
    import time
    current_time = time.time()
    
    # Token кэш хүчинтэй бол ашиглах
    if _bot_access_token and current_time < _token_expires_at:
        return _bot_access_token
    
    try:
        # Microsoft Bot Framework token endpoint
        token_url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
        
        # App ID болон Password шаардлагатай
        if not config.APP_ID or not config.APP_PASSWORD:
            print("⚠️ APP_ID болон APP_PASSWORD тохируулагдаагүй - authentication skip")
            return None
            
        # Token request
        token_data = {
            "grant_type": "client_credentials",
            "client_id": config.APP_ID,
            "client_secret": config.APP_PASSWORD,
            "scope": "https://api.botframework.com/.default"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as response:
                if response.status == 200:
                    token_response = await response.json()
                    
                    _bot_access_token = token_response.get("access_token")
                    expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
                    _token_expires_at = current_time + expires_in - 60  # 1 минутын өмнө expire
                    
                    print("✅ Bot Framework access token авсан")
                    return _bot_access_token
                else:
                    error_text = await response.text()
                    print(f"❌ Bot Framework token алдаа: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        print(f"Error getting Bot Framework token: {e}")
        traceback.print_exc()
        return None

# Create AI components
model: OpenAIModel

model = OpenAIModel(
    OpenAIModelOptions(
        api_key=config.OPENAI_API_KEY,
        default_model=config.OPENAI_MODEL_NAME,
    )
)

prompts = PromptManager(PromptManagerOptions(prompts_folder=f"{os.getcwd()}/prompts"))

planner = ActionPlanner(
    ActionPlannerOptions(
        model=model,
        prompts=prompts,
        default_prompt="chat",
        enable_feedback_loop=True,
    )
)

# Development mode configuration
if config.DEVELOPMENT_MODE:
    print("🧪 Development mode enabled - authentication bypass")
    # Development-д Teams adapter үүсгэхгүй
    storage = MemoryStorage()
    bot_app = None  # Teams framework ашиглахгүй
    
else:
    # Production mode - Full Teams AI framework
    print("🚀 Production mode - Full Teams authentication")
    storage = MemoryStorage()
    bot_app = Application[TurnState](
        ApplicationOptions(
            bot_app_id=config.APP_ID,
            storage=storage,
            adapter=TeamsAdapter(config),
            ai=AIOptions(planner=planner, enable_feedback_loop=True),
        )
    )

# FastAPI Request-г Teams AI bot-д дамжуулах
async def process_fastapi_request(fastapi_request):
    """FastAPI Request-г Teams AI framework рүү дамжуулах"""
    try:
        if config.DEVELOPMENT_MODE or bot_app is None:
            # Development mode - Teams framework ашиглахгүй
            print("Development mode: Teams framework bypassed")
            return {"status": "development_mode", "message": "Use /api/test endpoint for testing"}
            
        # Production mode - Teams AI framework ашиглах
        response = await bot_app.process(fastapi_request)
        return response
        
    except Exception as e:
        print(f"Error processing FastAPI request: {e}")
        traceback.print_exc()
        return None

# Development test mode - Authentication-гүйгээр OpenAI хариу авах
async def handle_test_message(user_message: str) -> str:
    """Development test mode - Bot Framework-гүйгээр OpenAI-тай шууд ярилцах"""
    try:
        # OpenAI 1.0+ client ашиглах
        from openai import AsyncOpenAI
        
        # AsyncOpenAI client үүсгэх  
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        # Chat completion хүсэлт илгээх
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": "Та туслах AI дэд юм. Монгол хэлээр хариулна уу. Найрсаг, тусламжтай байгаарай."
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Response-оос хариуг авах
        bot_response = response.choices[0].message.content.strip()
        return bot_response
        
    except Exception as e:
        print(f"Error in test mode: {e}")
        traceback.print_exc()
        return f"OpenAI API алдаа: {str(e)}"

# Teams Bot Connector API ашиглаж reply илгээх
async def send_teams_reply(service_url: str, conversation_id: str, activity_id: str, bot_response: str, app_id: str = None):
    """Teams Bot Connector API ашиглаж хариу илгээх"""
    try:
        # Reply URL үүсгэх
        reply_url = f"{service_url}v3/conversations/{conversation_id}/activities/{activity_id}"
        
        # Reply activity үүсгэх
        reply_activity = {
            "type": "message",
            "text": bot_response,
            "from": {
                "id": app_id or config.APP_ID or "bot-dev",
                "name": "Teams AI Bot"
            },
            "replyToId": activity_id
        }
        
        # Microsoft Bot Framework access token авах
        access_token = await get_bot_access_token()
        
        # HTTP client ашиглаж Teams Bot Connector API дуудах
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json"
            }
            
            # Bearer token нэмэх
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
                print("🔐 Using Bot Framework authentication token")
            else:
                print("⚠️ No Bot Framework token - attempting without authentication")
            
            print(f"🔗 Sending reply to: {reply_url}")
            print(f"📤 Reply activity: {json.dumps(reply_activity, indent=2)}")
            
            async with session.post(reply_url, json=reply_activity, headers=headers) as response:
                if response.status == 200 or response.status == 201:
                    print("✅ Teams reply sent successfully!")
                    return True
                else:
                    response_text = await response.text()
                    print(f"❌ Teams reply failed: {response.status} - {response_text}")
                    
                    # Token алдаа бол дахин оролдох
                    if response.status == 401 and access_token:
                        print("🔄 Token expired? Clearing cache and retrying...")
                        global _bot_access_token, _token_expires_at
                        _bot_access_token = None
                        _token_expires_at = 0
                    
                    return False
                    
    except Exception as e:
        print(f"Error sending Teams reply: {e}")
        traceback.print_exc()
        return False

# Microsoft Teams activity format ойлгох 
async def handle_teams_message(user_message: str, teams_activity: dict) -> dict:
    """Microsoft Teams activity-г ойлгож, OpenAI шууд ашиглах, Teams reply илгээх"""
    try:
        # OpenAI 1.0+ client ашиглах
        from openai import AsyncOpenAI
        
        # Teams activity-аас context мэдээлэл авах
        user_name = teams_activity.get("from", {}).get("name", "User")
        conversation_id = teams_activity.get("conversation", {}).get("id", "unknown")
        activity_id = teams_activity.get("id", "unknown")
        service_url = teams_activity.get("serviceUrl", "")
        
        # AsyncOpenAI client үүсгэх  
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        
        # Teams context-тэй system prompt
        system_prompt = f"""
Та Microsoft Teams-д ажилладаг туслах AI bot юм. 
Хэрэглэгчтэй {user_name} гэж нэрлэдэг.
Монгол хэлээр найрсаг, тусламжтай хариулна уу.
Teams орчинд ажиллаж байгаагаа санаарай.
"""
        
        # Chat completion хүсэлт илгээх
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_message
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Response-оос хариуг авах
        bot_response = response.choices[0].message.content.strip()
        
        # Teams activity logging
        print(f"📢 Teams message from {user_name}: {user_message}")
        print(f"🤖 Bot response: {bot_response}")
        
        # Teams client рүү reply илгээх (зөвхөн TEAMS_REPLY_ENABLED=true бол)
        reply_success = False
        reply_attempted = False
        
        if config.TEAMS_REPLY_ENABLED:
            if service_url and conversation_id and activity_id:
                reply_attempted = True
                reply_success = await send_teams_reply(
                    service_url=service_url,
                    conversation_id=conversation_id, 
                    activity_id=activity_id,
                    bot_response=bot_response
                )
            else:
                print("⚠️ Teams reply enabled but missing required fields")
        else:
            print("ℹ️ Teams reply disabled - only console logging")
            print("💡 To enable Teams replies: set TEAMS_REPLY_ENABLED=true and configure BOT_ID/BOT_PASSWORD")
        
        return {
            "bot_response": bot_response,
            "reply_sent": reply_success,
            "reply_attempted": reply_attempted,
            "teams_reply_enabled": config.TEAMS_REPLY_ENABLED,
            "teams_context": {
                "user": user_name,
                "conversation_id": conversation_id,
                "activity_id": activity_id,
                "service_url": service_url
            }
        }
        
    except Exception as e:
        print(f"Error in Teams message handling: {e}")
        traceback.print_exc()
        return {
            "bot_response": f"Teams OpenAI алдаа: {str(e)}",
            "reply_sent": False,
            "reply_attempted": False,
            "error": str(e)
        }

# Teams AI framework event handlers (зөвхөн production mode-д)
if not config.DEVELOPMENT_MODE and bot_app is not None:
    @bot_app.error
    async def on_error(context: TurnContext, error: Exception):
        # This check writes out errors to console log .vs. app insights.
        # NOTE: In production environment, you should consider logging this to Azure
        #       application insights.
        print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
        traceback.print_exc()

        # Send a message to the user
        await context.send_activity("The agent encountered an error or bug.")

    @bot_app.feedback_loop()
    async def feedback_loop(_context: TurnContext, _state: TurnState, feedback_loop_data: FeedbackLoopData):
        # Add custom feedback process logic here.
        print(f"Your feedback is:\n{json.dumps(asdict(feedback_loop_data), indent=4)}")

else:
    print("🧪 Development mode: Teams AI event handlers disabled")