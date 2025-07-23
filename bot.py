import os
import sys
import json
import traceback
from dataclasses import asdict

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

# Microsoft Teams activity format ойлгох 
async def handle_teams_message(user_message: str, teams_activity: dict) -> str:
    """Microsoft Teams activity-г ойлгож, OpenAI шууд ашиглах"""
    try:
        # OpenAI 1.0+ client ашиглах
        from openai import AsyncOpenAI
        
        # Teams activity-аас context мэдээлэл авах
        user_name = teams_activity.get("from", {}).get("name", "User")
        conversation_id = teams_activity.get("conversation", {}).get("id", "unknown")
        
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
        
        return bot_response
        
    except Exception as e:
        print(f"Error in Teams message handling: {e}")
        traceback.print_exc()
        return f"Teams OpenAI алдаа: {str(e)}"

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