import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import init_db, upsert_user, get_user, save_user_prompt, list_user_prompts, delete_user_prompt, get_user_prompt

async def main():
    print("Initializing DB...")
    await init_db()
    
    # Test User
    print("Upserting user...")
    user = await upsert_user(12345, "prompt_tester", "en")
    print("User quality setting:", user.image_quality)
    print("User transparent setting:", user.image_transparent)
    
    # Test Prompts
    print("Saving prompt...")
    pid = await save_user_prompt(user.id, "Test Title", "A portrait of a red wolf in winter forest --ar 16:9")
    print("Saved prompt ID:", pid)
    
    prompts = await list_user_prompts(user.id)
    print("User prompts total:", len(prompts))
    print("First prompt details:", prompts[0])
    
    saved = await get_user_prompt(user.id, pid)
    print("Get prompt returned:", saved)
    
    deleted = await delete_user_prompt(user.id, pid)
    print("Deleted prompt success:", deleted)
    
    prompts_after = await list_user_prompts(user.id)
    print("User prompts total after delete:", len(prompts_after))

if __name__ == "__main__":
    asyncio.run(main())
