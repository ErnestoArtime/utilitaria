import asyncio
import os

from app.main import process_whatsapp_outbox_once


async def main():
    interval = max(2, int(os.getenv("OUTBOX_INTERVAL_SECONDS", "5")))
    while True:
        try:
            result = await asyncio.to_thread(process_whatsapp_outbox_once)
            if result["processed"]:
                print(f"whatsapp outbox: {result}", flush=True)
        except Exception as exc:
            print(f"whatsapp outbox failed: {exc}", flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
