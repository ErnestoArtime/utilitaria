import asyncio
from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

import httpx


def gas_interval_seconds(now: datetime | None = None) -> int:
    cuba_now = now or datetime.now(ZoneInfo("America/Havana"))
    minutes = cuba_now.hour * 60 + cuba_now.minute
    peak = 19 * 60 + 30 <= minutes < 21 * 60 + 30
    setting = "GAS_PEAK_INTERVAL_SECONDS" if peak else "GAS_OFFPEAK_INTERVAL_SECONDS"
    default = "60" if peak else "900"
    return max(60, int(os.getenv(setting, default)))


async def main():
    solar_interval = max(60, int(os.getenv("SOLAR_CHECK_INTERVAL_SECONDS", "300")))
    service_token = os.getenv("SERVICE_API_TOKEN", "")
    api_key = os.getenv("API_KEY", "")
    headers = (
        {"Authorization": f"Bearer {service_token}"}
        if service_token
        else {"X-API-Key": api_key}
        if api_key
        else {}
    )
    async with httpx.AsyncClient(timeout=90, headers=headers) as client:
        next_gas_check = 0.0
        next_solar_check = 0.0
        while True:
            current = time.monotonic()
            checks = []
            if current >= next_gas_check:
                checks.append(("gas-10kg-goniogas", gas_interval_seconds()))
            if current >= next_solar_check:
                checks.append(("tiendasolar-catalog", solar_interval))
            for slug, interval in checks:
                try:
                    response = await client.post(
                        f"http://api:8080/api/alerts/{slug}/check"
                    )
                    response.raise_for_status()
                    print(f"{slug} check completed: {response.text}", flush=True)
                    next_check = time.monotonic() + interval
                except Exception as exc:
                    print(f"{slug} check failed: {exc}", flush=True)
                    next_check = time.monotonic() + 15
                if slug == "gas-10kg-goniogas":
                    next_gas_check = next_check
                else:
                    next_solar_check = next_check
            await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
