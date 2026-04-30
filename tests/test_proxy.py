import os
import httpx

os.environ["HTTP_PROXY"] = "http://127.0.0.1:9674"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9674"
os.environ["NO_PROXY"] = "ai.comfly.chat,127.0.0.1"

try:
    with httpx.Client(timeout=5) as client:
        r = client.get("https://ai.comfly.chat/v1/models")
        print(f"COMFLY REACHED: {r.status_code}")
except Exception as e:
    print(f"COMFLY FAILED: {str(e)}")
