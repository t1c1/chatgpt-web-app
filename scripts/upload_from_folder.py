#!/usr/bin/env python3
"""
Simple script to upload all ChatGPT and Claude export files from a folder.
Just drop your conversations.json files here and run this script!
"""

import os
import sys
import requests
from pathlib import Path

# Configuration
UPLOAD_FOLDER = Path(__file__).parent / "uploads_inbox"
API_URL = "http://localhost:8001/api/v1"

def upload_file(file_path: Path):
    """Upload a single file to the API."""
    
    # Determine provider based on file content or name
    # You can customize this logic
    provider = "chatgpt"  # Default to ChatGPT
    
    # Try to detect from filename
    if "claude" in file_path.name.lower():
        provider = "claude"
    
    endpoint = f"{API_URL}/uploads/{provider}"
    
    print(f"📤 Uploading {file_path.name} as {provider.upper()} export...")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/json')}
            response = requests.post(endpoint, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Processed {result.get('processing_stats', {}).get('conversations_processed', 0)} conversations")
            print(f"   Messages: {result.get('processing_stats', {}).get('messages_processed', 0)}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Process all files in the upload folder."""
    
    # Create upload folder if it doesn't exist
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("🚀 ChatGPT/Claude Export Uploader")
    print("=" * 60)
    print(f"\n📁 Watching folder: {UPLOAD_FOLDER.absolute()}")
    print(f"🌐 API endpoint: {API_URL}")
    print()
    
    # Check if API is running
    try:
        response = requests.get(f"{API_URL.replace('/api/v1', '')}/health")
        if response.status_code != 200:
            print("❌ API is not responding. Make sure Docker is running!")
            print("   Run: docker-compose up -d")
            sys.exit(1)
    except:
        print("❌ Cannot connect to API at http://localhost:8001")
        print("   Make sure the app is running with: docker-compose up -d")
        sys.exit(1)
    
    print("✅ API is running!\n")
    
    # Find all JSON and ZIP files
    files = list(UPLOAD_FOLDER.glob("*.json")) + list(UPLOAD_FOLDER.glob("*.zip"))
    
    if not files:
        print("📝 No files found in the upload folder.")
        print(f"\n💡 To upload your exports:")
        print(f"   1. Copy your conversations.json files to: {UPLOAD_FOLDER.absolute()}")
        print(f"   2. Run this script again: python3 {__file__}")
        print(f"\n   OR just drag and drop your files into: {UPLOAD_FOLDER.absolute()}")
        return
    
    print(f"Found {len(files)} file(s) to process:\n")
    
    success_count = 0
    for file_path in files:
        if upload_file(file_path):
            success_count += 1
            # Optionally move processed files
            processed_folder = UPLOAD_FOLDER / "processed"
            processed_folder.mkdir(exist_ok=True)
            new_path = processed_folder / file_path.name
            file_path.rename(new_path)
            print(f"   Moved to: {new_path}\n")
        print()
    
    print("=" * 60)
    print(f"✨ Complete! Successfully uploaded {success_count}/{len(files)} files")
    print("=" * 60)
    print(f"\n🔍 Now search your conversations at: http://localhost:8001/docs")


if __name__ == "__main__":
    main()

