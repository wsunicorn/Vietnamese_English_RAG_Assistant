import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            r = await s.get("https://animevietsub.name/")
            print(f"Status: {r.status_code}")
            print(f"Text preview: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
