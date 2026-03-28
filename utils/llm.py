import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.1-8b-instant"


def chat(system_prompt: str, user_prompt: str) -> str:
    """
    Simple wrapper around the API call.
    Every agent calls this instead of calling the API directly.
    This way if we ever switch models, we change it in ONE place only.
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0  # 0 = deterministic, important for structured extraction
    )
    return response.choices[0].message.content.strip()