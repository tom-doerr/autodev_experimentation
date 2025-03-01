#!/usr/bin/env python

import os
from dotenv import load_dotenv

def debug_key():
    # Check if key exists before loading .env
    print("Before loading .env:")
    key_before = os.environ.get("OPENROUTER_API_KEY")
    print(f"  OPENROUTER_API_KEY = {key_before!r}")
    
    # Load from .env file
    print("\nLoading .env file...")
    load_dotenv(override=True)
    
    # Check key after loading .env
    print("\nAfter loading .env:")
    key_after = os.environ.get("OPENROUTER_API_KEY")
    print(f"  OPENROUTER_API_KEY = {key_after!r}")
    
    # Check for placeholder
    if key_after == "your-api-key-here":
        print("\nWARNING: Key is still set to the placeholder value!")
    elif not key_after:
        print("\nWARNING: Key is None or empty after loading .env!")
    else:
        print(f"\nKey appears valid (length: {len(key_after)})")
        
    # Check the contents of .env file
    try:
        with open(".env", "r") as f:
            env_content = f.read().strip()
            print("\n.env file content (masked):")
            if "OPENROUTER_API_KEY=" in env_content:
                key_part = env_content.split("OPENROUTER_API_KEY=", 1)[1]
                if key_part:
                    print(f"  OPENROUTER_API_KEY=[MASKED, length: {len(key_part)}]")
                else:
                    print("  OPENROUTER_API_KEY= (empty value)")
            else:
                print("  No OPENROUTER_API_KEY found in .env file")
    except Exception as e:
        print(f"\nError reading .env file: {e}")

if __name__ == "__main__":
    debug_key()
