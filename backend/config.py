"""
Configuration settings for SailPoint Support Bot
"""

import os

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# SailPoint Configuration
SAILPOINT_API_URL = os.getenv("SAILPOINT_API_URL", "")
SAILPOINT_CLIENT_ID = os.getenv("SAILPOINT_CLIENT_ID", "")
SAILPOINT_CLIENT_SECRET = os.getenv("SAILPOINT_CLIENT_SECRET", "")

# Application Settings
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# CORS Settings
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173"
]

# LLM Settings
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 500
