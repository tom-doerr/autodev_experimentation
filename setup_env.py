#!/usr/bin/env python

import os
import re
import subprocess

def extract_api_key_from_zshrc():
    """Extract the OpenRouter API key from zshrc file."""
    home_dir = os.path.expanduser("~")
    zshrc_path = os.path.join(home_dir, ".zshrc")
    
    try:
        # Method 1: Check if it's already in environment
        key = os.environ.get('OPENROUTER_API_KEY')
        if key:
            print("Found API key in current environment.")
            return key
            
        if os.path.exists(zshrc_path):
            # Method 2: Read the file directly
            with open(zshrc_path, 'r') as f:
                zshrc_content = f.read()
                
            # Look for export statements with OPENROUTER_API_KEY
            matches = re.findall(r'export\s+OPENROUTER_API_KEY=[\'"](.*?)[\'"]', zshrc_content)
            if matches:
                print("Found API key in .zshrc file.")
                return matches[0]
        
        # Method 3: Try to source the zshrc and echo the variable
        try:
            result = subprocess.run(
                ['zsh', '-c', 'source ~/.zshrc && echo $OPENROUTER_API_KEY'],
                capture_output=True,
                text=True,
                check=True
            )
            key = result.stdout.strip()
            if key:
                print("Found API key by sourcing .zshrc.")
                return key
        except (subprocess.SubprocessError, subprocess.CalledProcessError):
            pass
    
    except Exception as e:
        print(f"Error extracting API key: {e}")
    
    return None

def create_env_file(api_key):
    """Create a .env file with the API key."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # Check if .env already exists
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            current_content = f.read()
        
        # Check if the API key is already in the file
        if f"OPENROUTER_API_KEY={api_key}" in current_content:
            print(f".env file already contains the correct API key.")
            return env_path
            
        # Backup the existing file
        backup_path = f"{env_path}.bak"
        with open(backup_path, 'w') as f:
            f.write(current_content)
        print(f"Backed up existing .env file to {backup_path}")
    
    with open(env_path, 'w') as f:
        f.write(f"OPENROUTER_API_KEY={api_key}\n")
    
    print(f".env file created at {env_path}")
    return env_path

def main():
    api_key = extract_api_key_from_zshrc()
    
    if api_key:
        print("OpenRouter API key found!")
        env_path = create_env_file(api_key)
        print(f"API key has been saved to {env_path}")
    else:
        print("Could not find OpenRouter API key in .zshrc")
        manual_key = input("Please enter your OpenRouter API key manually: ")
        if manual_key.strip():
            env_path = create_env_file(manual_key.strip())
            print(f"API key has been saved to {env_path}")
        else:
            print("No API key provided. Exiting.")

if __name__ == "__main__":
    main()
