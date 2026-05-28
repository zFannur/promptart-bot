import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from utils.prompt_builder import parse_midjourney_flags, build_prompt
from utils.prompt_templates import TRENDING_TEMPLATES
from services.database import init_db, save_user_prompt, list_user_prompts, delete_user_prompt, get_user_prompt, upsert_user


def test_parser():
    print("=== Testing Midjourney Parser ===")
    test_cases = [
        ("a cute cat", "a cute cat", {}),
        ("a cute cat --ar 16:9", "a cute cat", {"aspect_ratio": "16:9"}),
        ("a cute cat --ar 9/16 --seed 123", "a cute cat", {"aspect_ratio": "9:16", "seed": 123}),
        ("a cute cat --no water, ugly, blurry --seed 456 --ar 4x5", "a cute cat", {"aspect_ratio": "4:5", "seed": 456, "negative_prompt": "water, ugly, blurry"}),
        ("a cybernetic wolf --seed 999 --no text, glow", "a cybernetic wolf", {"seed": 999, "negative_prompt": "text, glow"}),
    ]

    for raw, expected_prompt, expected_overrides in test_cases:
        p, o = parse_midjourney_flags(raw)
        print(f"Raw: {raw!r}")
        print(f"  Parsed prompt: {p!r} (Expected: {expected_prompt!r})")
        print(f"  Overrides: {o} (Expected: {expected_overrides})")
        assert p == expected_prompt, f"Prompt mismatch: {p!r} != {expected_prompt!r}"
        assert o == expected_overrides, f"Overrides mismatch: {o} != {expected_overrides}"
        print("  [PASS]")


def test_builder():
    print("\n=== Testing Prompt Builder ===")
    prompt = build_prompt("a glowing portal", "neon", "aerial", "canon")
    expected = "a glowing portal, soft neon glow, cyberpunk ambient light, aerial drone shot, bird's eye view, captured on Canon EOS R5 DSLR, sharp focus, high-end photography"
    print(f"Built prompt: {prompt!r}")
    assert prompt == expected, f"Prompt mismatch: {prompt!r} != {expected!r}"
    print("  [PASS]")


async def test_db_prompts():
    print("\n=== Testing DB Prompt Methods ===")
    await init_db()
    # Ensure test user exists
    user = await upsert_user(888888, "prompt_test_user", "ru")
    
    # Save a prompt
    title = "Test Prompt"
    prompt_text = "a beautiful fantasy forest --ar 16:9"
    pid = await save_user_prompt(user.id, title, prompt_text)
    print(f"Saved prompt with ID: {pid}")
    
    # Retrieve
    p = await get_user_prompt(user.id, pid)
    print(f"Retrieved: {p}")
    assert p["title"] == title
    assert p["prompt_text"] == prompt_text
    
    # List
    plist = await list_user_prompts(user.id)
    print(f"List: {plist}")
    assert len(plist) > 0
    
    # Delete
    deleted = await delete_user_prompt(user.id, pid)
    print(f"Deleted successfully: {deleted}")
    assert deleted is True
    
    # Check deletion
    p_deleted = await get_user_prompt(user.id, pid)
    print(f"Retrieved after deletion: {p_deleted}")
    assert p_deleted is None
    print("  [PASS]")


async def main():
    test_parser()
    test_builder()
    await test_db_prompts()
    print("\nAll unit tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
