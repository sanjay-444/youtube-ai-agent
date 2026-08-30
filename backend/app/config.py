import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL")


settings = Settings()