import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://gen.pollinations.ai/models")
        data = resp.json()
        
        video_models = [m for m in data if "video" in m.get("output_modalities", [])]
        print(f"Found {len(video_models)} video models.")
        for m in video_models:
            print("---")
            print(json.dumps(m, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
