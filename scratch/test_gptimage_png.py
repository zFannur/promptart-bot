import asyncio
import httpx
import urllib.parse
from PIL import Image
import io
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

async def test_gptimage_png():
    headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}
    prompt = "a cute 3D vector illustration of a red strawberry, sticker style, transparent background"
    encoded_prompt = urllib.parse.quote(prompt)
    
    url = f"https://gen.pollinations.ai/image/{encoded_prompt}"
    
    # Let's test with different query param formats
    params = {
        "model": "gptimage",
        "width": 1024,
        "height": 1024,
        "quality": "hd",
        "transparent": "true", # also try passing as boolean or '1'
        "seed": 42
    }
    
    print(f"Requesting GET URL: {url} with params {params}")
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        print("Status code:", resp.status_code)
        print("Response headers:", dict(resp.headers))
        if resp.status_code == 200:
            print("Success! Generated image size:", len(resp.content), "bytes")
            img = Image.open(io.BytesIO(resp.content))
            print("Pillow format:", img.format)
            print("Pillow mode:", img.mode)
            output_path = Path("scratch/test_strawberry_transparent.png")
            output_path.write_bytes(resp.content)
            print("Saved to:", output_path.absolute())
        else:
            print("Error body:", resp.text)

if __name__ == "__main__":
    asyncio.run(test_gptimage_png())
