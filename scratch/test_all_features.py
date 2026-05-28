import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import init_db, get_user, upsert_user
from services.pollinations import pollinations, ModelInfo


async def test():
    print("=== Testing DB Migrations ===")
    try:
        await init_db()
        print("Database initialized successfully.")
        
        # Test upserting a test user and check that new setting columns exist
        user = await upsert_user(999999, "test_user", "en")
        print("User settings:")
        print(f"  video_model: {getattr(user, 'video_model', None)}")
        print(f"  video_aspect_ratio: {getattr(user, 'video_aspect_ratio', None)}")
        print(f"  video_duration: {getattr(user, 'video_duration', None)}")
        print(f"  audio_model: {getattr(user, 'audio_model', None)}")
        print(f"  audio_voice: {getattr(user, 'audio_voice', None)}")
        print(f"  text_model: {getattr(user, 'text_model', None)}")
    except Exception as e:
        print("DB migration failed:", e)

    print("\n=== Testing Modality Model Listings ===")
    for mod in ["image", "video", "audio", "text"]:
        try:
            models = await pollinations.list_models(mod, force_refresh=True)
            print(f"Modality '{mod}' total models: {len(models)}")
            print(f"  Top 3 models: {[m.name for m in models[:3]]}")
        except Exception as e:
            print(f"Failed to fetch '{mod}' models:", e)

    print("\n=== Testing Chat Text Generation ===")
    try:
        response = await pollinations.generate_text("Say 'Hello World' in Russian", model="openai")
        print("AI Response:", response)
    except Exception as e:
        print("Chat generation failed:", e)

    print("\n=== Testing Audio Generation ===")
    try:
        audio_bytes = await pollinations.generate_audio("Hello", model="openai-audio", voice="nova")
        print(f"Audio bytes generated: {len(audio_bytes)} bytes")
    except Exception as e:
        print("Audio generation failed:", e)


if __name__ == "__main__":
    asyncio.run(test())
