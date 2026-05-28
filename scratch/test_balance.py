import asyncio
import sys
from pathlib import Path

# Add project root to sys.path so we can import services
sys.path.append(str(Path(__file__).parent.parent))

from services.pollinations import pollinations, BalanceUnavailable, BalanceInfo


async def test():
    print("=== Testing Models ===")
    try:
        models = await pollinations.list_image_models(force_refresh=True)
        print(f"Total image models retrieved: {len(models)}")
        paid_models = [m for m in models if m.paid_only]
        print(f"Paid models found: {[m.name for m in paid_models]}")
        print("Model selection list example:")
        for m in models[:5]:
            paid_tag = " [paid]" if m.paid_only else ""
            print(f" - {m.name}{paid_tag} ({m.price_pollen} pollen)")
    except Exception as e:
        print("Failed to fetch models:", e)

    print("\n=== Testing Balance ===")
    try:
        bal = await pollinations.get_balance()
        if isinstance(bal, BalanceUnavailable):
            print("Balance unavailable:", bal.reason)
        else:
            print("Balance retrieved successfully:")
            print(f"  Total: {bal}")
            if isinstance(bal, BalanceInfo):
                print(f"  Tier:  {bal.tier_balance}")
                print(f"  Paid:  {bal.paid_balance}")
            else:
                print("  Type is not BalanceInfo!")
    except Exception as e:
        print("Failed to get balance:", e)


if __name__ == "__main__":
    asyncio.run(test())
