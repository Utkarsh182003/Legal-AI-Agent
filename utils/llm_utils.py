import os
from dotenv import load_dotenv

def load_api_key_from_env():
    """
    Loads environment variables from .env file.
    This function should be called at the very start of your main script.
    """
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY environment variable not set or not found in .env file. LLM API calls may fail.")
    else:
        print("GOOGLE_API_KEY loaded successfully from environment.")



