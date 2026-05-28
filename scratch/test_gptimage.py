import asyncio
import httpx
import urllib.parse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

async def test_gptimage():
    headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}
    prompt = "a cute 3D vector illustration of a red strawberry, solid background"
    encoded_prompt = urllib.parse.quote(prompt)
    
    url = f"https://gen.pollinations.ai/image/{encoded_prompt}"
    params = {
        "model": "gptimage",
        "width": 1024,
        "height": 1024,
        "quality": "hd",
        "transparent": "true",
        "seed": 42
    }
    
    print(f"Requesting GET URL: {url} with params {params}")
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        print("Status code:", resp.status_code)
        print("Response headers:", dict(resp.headers))
        if resp.status_code == 200:
            print("Success! Generated image size:", len(resp.content), "bytes")
            # Save it locally to verify it's valid
            output_path = Path("scratch/test_strawberry.png")
            output_path.write_bytes(resp.content)
            print(f"Image saved to: {output_path.absolute()}")
        else:
            print("Error body:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_gptimage())
