# # utils/llm_utils.py (REFACTORED)

# import os
# from dotenv import load_dotenv

# def load_api_key_from_env():
#     """
#     Loads environment variables from .env file.
#     This function should be called at the very start of your main script.
#     """
#     load_dotenv()
#     if not os.getenv("GROQ_API_KEY"):
#         print("Warning: GROQ_API_KEY environment variable not set or not found in .env file. LLM API calls may fail.")
#     else:
#         print("GROQ_API_KEY loaded successfully from environment.")

# # We no longer define our custom GroqModel here.
# # Instead, we will import pydantic_ai.models.groq.GroqModel directly
# # where it's needed (e.g., in main.py for instantiation).

# # This keeps the llm_utils.py file focused on environment loading and utility functions.
# #         doc.save(file_path)

# utils/llm_utils.py (UPDATED for Google Gemini)

import os
from dotenv import load_dotenv # Import load_dotenv

def load_api_key_from_env():
    """
    Loads environment variables from .env file.
    This function should be called at the very start of your main script.
    """
    load_dotenv()
    # Check for GOOGLE_API_KEY now
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY environment variable not set or not found in .env file. LLM API calls may fail.")
    else:
        print("GOOGLE_API_KEY loaded successfully from environment.")

# Our custom GroqModel is no longer needed.
# We will use pydantic_ai.models.google.GoogleModel directly.

