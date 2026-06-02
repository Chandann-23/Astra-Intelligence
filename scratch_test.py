import asyncio
from tenacity import retry, stop_after_attempt, RetryError

class RateLimitError(Exception):
    pass

@retry(stop=stop_after_attempt(3))
async def _fail():
    print("Trying...")
    raise RateLimitError("Rate limit exceeded")

async def main():
    try:
        await _fail()
    except RetryError as e:
        print("Caught RetryError successfully:", type(e))
    except Exception as e:
        print("Caught something else:", type(e))

asyncio.run(main())
