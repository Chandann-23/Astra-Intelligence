import os
import asyncio
import litellm
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("No GOOGLE_API_KEY")
        return
        
    models_to_test = [
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-flash-latest",
        "gemini/gemini-pro"
    ]
    
    for m in models_to_test:
        print(f"Testing {m}...")
        try:
            response = await litellm.acompletion(
                model=m,
                messages=[{"role": "user", "content": "hi"}],
                api_key=api_key
            )
            print("SUCCESS:", m)
        except Exception as e:
            print("FAILED:", m, str(e))

asyncio.run(test())
