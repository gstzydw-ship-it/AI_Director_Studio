from crewai import LLM

try:
    llm1 = LLM(
        model="claude-opus-4-6",
        api_key="sk-REDACTED",
        base_url="https://ai.comfly.chat/v1"
    )
    print("SUCCESS with pure model name!")
except Exception as e:
    print("FAILED pure:", str(e))

try:
    llm2 = LLM(
        model="openai/claude-opus-4-6",
        api_key="sk-REDACTED",
        base_url="https://ai.comfly.chat/v1"
    )
    print("SUCCESS with openai/ prefix!")
except Exception as e:
    print("FAILED prefix:", str(e))


