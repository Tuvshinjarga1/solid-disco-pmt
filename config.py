"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot Configuration"""

    # Railway платформ дээр PORT environment variable автоматаар тохируулагддаг
    PORT = int(os.environ.get("PORT", 3978))
    
    # Development mode - authentication bypass хийх эсэх
    DEVELOPMENT_MODE = os.environ.get("DEVELOPMENT_MODE", "true").lower() == "true"
    
    # Teams reply feature enable/disable
    TEAMS_REPLY_ENABLED = os.environ.get("TEAMS_REPLY_ENABLED", "false").lower() == "true"
    
    APP_ID = os.environ.get("BOT_ID", "")
    APP_PASSWORD = os.environ.get("BOT_PASSWORD", "")
    APP_TYPE = os.environ.get("BOT_TYPE", "")
    APP_TENANTID = os.environ.get("BOT_TENANT_ID", "")
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"] # OpenAI API key
    OPENAI_MODEL_NAME='gpt-3.5-turbo' # OpenAI model name. You can use any other model name from OpenAI.
