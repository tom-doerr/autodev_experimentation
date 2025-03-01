#!/usr/bin/env python

import os

def update_api_key():
    """Update the API key in the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    print("This script will update your OpenRouter API key in the .env file.")
    api_key = input("Please enter your OpenRouter API key: ")
    
    if not api_key.strip():
        print("No API key provided. Exiting.")
        return
    
    with open(env_path, 'w') as f:
        f.write(f"OPENROUTER_API_KEY={api_key.strip()}\n")
    
    print(f"API key has been updated in {env_path}")

if __name__ == "__main__":
    update_api_key()
