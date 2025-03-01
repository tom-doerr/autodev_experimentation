#!/usr/bin/env python
import os
import subprocess
import sys

def get_key_from_zshrc():
    try:
        result = subprocess.run(
            ["zsh", "-c", "source ~/.zshrc >/dev/null 2>&1 && echo $OPENROUTER_API_KEY"],
            capture_output=True,
            text=True,
            check=True
        )
        key = result.stdout.strip()
        
        if key and key != "your-api-key-here":
            print(f"Found API key (length: {len(key)}) - first 4 chars: {key[:4]}...")
            return key
        else:
            print(f"Found placeholder or empty key in zshrc: '{key}'")
            return None
    except Exception as e:
        print(f"Error extracting key: {e}")
        return None

if __name__ == "__main__":
    key = get_key_from_zshrc()
    if key:
        print("\nDo you want to save this key to .env? (y/n): ", end="")
        answer = input().strip().lower()
        if answer == "y":
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
            with open(env_path, "w") as f:
                f.write(f"OPENROUTER_API_KEY={key}\n")
            print(f"Key saved to {env_path}")
            
            # Test if dotenv loads it properly
            import dotenv
            dotenv.load_dotenv(env_path)
            loaded_key = os.environ.get("OPENROUTER_API_KEY")
            if loaded_key == key:
                print("Verified: Key loads properly with dotenv!")
            else:
                print("Warning: Key does not load properly with dotenv")
        else:
            print("Key not saved.")
    else:
        print("\nNo valid API key found in zshrc")
