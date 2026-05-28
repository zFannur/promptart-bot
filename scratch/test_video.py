import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from services.pollinations import pollinations

async def test_video():
    print("Testing video generation with ltx-2...")
    try:
        video_bytes, seed = await pollinations.generate_video(
            prompt="a cat playing with yarn, 3d render, cinematic",
            width=1024,
            height=576,
            model="ltx-2",
            seconds=5
        )
        print(f"Success! Generated {len(video_bytes)} bytes. Seed: {seed}")
    except Exception as e:
        print("Video generation failed:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_video())
