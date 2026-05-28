import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from services.pollinations import pollinations

async def test_chat_context():
    print("Testing chat context...")
    history = [
        {"role": "user", "content": "My name is John. I live in Paris."},
        {"role": "assistant", "content": "Hello John! Paris is a beautiful city. How can I help you today?"},
        {"role": "user", "content": "What is my name and where do I live?"}
    ]
    try:
        response = await pollinations.generate_text(
            messages=history,
            model="openai"
        )
        print("Response received:")
        print(response)
        
        # Check if the response contains the correct name and city to verify context working
        if "john" in response.lower() and "paris" in response.lower():
            print("\nSUCCESS! The AI remembered the context!")
        else:
            print("\nWARNING: The AI did not seem to use the context. Please check.")
            
    except Exception as e:
        print("Chat context call failed:", e)

if __name__ == "__main__":
    asyncio.run(test_chat_context())
