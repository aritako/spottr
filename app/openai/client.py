from app.config import settings
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
