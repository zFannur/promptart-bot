import asyncio
import httpx
import urllib.parse
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

async def test_video_get():
    headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}
    prompt = "a cute fluffy orange kitten playing with yarn, 3d animation"
    encoded_prompt = urllib.parse.quote(prompt)
    
    # We use a GET request
    url = f"https://gen.pollinations.ai/video/{encoded_prompt}"
    params = {
        "model": "ltx-2",
        "width": 1024,
        "height": 576,
        "duration": 5,
        "seed": 42
    }
    
    print(f"Requesting URL: {url} with params {params}")
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        print("Status code:", resp.status_code)
        print("Response headers:", dict(resp.headers))
        if resp.status_code == 200:
            content_len = len(resp.content)
            print(f"Success! Response body length: {content_len} bytes")
            # Let's save a few bytes to verify it's an mp4 or file
            print("First 16 bytes:", resp.content[:16])
        else:
            print("Error body:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_video_get())
