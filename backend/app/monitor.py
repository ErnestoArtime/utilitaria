import asyncio
import os

import httpx


async def main():
    interval = max(60, int(os.getenv("ALERT_CHECK_INTERVAL_SECONDS", "300")))
    api_key = os.getenv("API_KEY", "")
    headers = {"X-API-Key": api_key} if api_key else {}
    async with httpx.AsyncClient(timeout=90, headers=headers) as client:
        while True:
            delay = interval
            try:
                response = await client.post("http://api:8080/api/alerts/check")
                response.raise_for_status()
                print(f"alert check completed: {response.text}", flush=True)
            except Exception as exc:
                print(f"alert check failed: {exc}", flush=True)
                delay = 15
            await asyncio.sleep(delay)


if __name__ == "__main__":
    asyncio.run(main())
