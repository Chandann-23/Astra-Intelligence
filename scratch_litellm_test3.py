import os
import asyncio
import litellm

async def test():
    api_key = None
    try:
        with open('.env', 'rb') as f:
            content = f.read().decode('utf-16-le', errors='ignore')
            for line in content.splitlines():
                if line.startswith('GOOGLE_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
    except Exception as e:
        pass

    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("No key")
        return
        
    models_to_test = [
        "gemini/gemini-2.0-flash",
        "gemini/gemini-2.0-flash-exp",
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.0-pro"
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
