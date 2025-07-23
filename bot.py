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

# Define storage and application
storage = MemoryStorage()
bot_app = Application[TurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
        ai=AIOptions(planner=planner, enable_feedback_loop=True),
    )
)

# FastAPI Request-г шууд Teams AI bot-д дамжуулах
async def process_fastapi_request(fastapi_request):
    """FastAPI Request-г Teams AI framework рүү шууд дамжуулах"""
    try:
        # Teams AI framework нь FastAPI Request-тэй шууд ажиллана
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