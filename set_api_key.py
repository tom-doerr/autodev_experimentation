#!/usr/bin/env python

import os

def main():
    print("Enter your OpenRouter API key: ", end="")
    api_key = input().strip()
    
    if not api_key:
        print("Error: No API key provided")
        return
    
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    with open(env_path, 'w') as f:
        f.write(f"OPENROUTER_API_KEY={api_key}\n")
    
    print(f"API key successfully saved to {env_path}")

if __name__ == "__main__":
    main()
