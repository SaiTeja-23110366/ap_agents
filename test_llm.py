from utils.llm import chat

response = chat(
    system_prompt="You are a helpful assistant. Reply in one sentence only.",
    user_prompt="What is an invoice?"
)
print(response)