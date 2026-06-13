#!/usr/bin/env python3
"""
Automated downloader for SLM GGUF models.
Downloads Qwen's Qwen2.5-1.5B-Instruct-GGUF (Q4_K_M) from Hugging Face.
"""

import os
import sys
import urllib.request
from pathlib import Path

# Approved GGUF model details
DEFAULT_MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_DEST_PATH = Path(__file__).parent.parent / "backend" / "models" / "qwen2.5-1.5b-instruct-gguf" / "model.gguf"


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def download_progress_hook(count, block_size, total_size):
    """Callback for urllib.request.urlretrieve progress reporting."""
    downloaded = count * block_size
    percent = min(100, int(downloaded * 100 / total_size))
    
    # Format progress bar
    bar_length = 40
    filled_length = int(bar_length * percent // 100)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    
    sys.stdout.write(
        f"\rDownloading: |{bar}| {percent}% ({format_size(downloaded)} / {format_size(total_size)})"
    )
    sys.stdout.flush()


def download_model(url: str = DEFAULT_MODEL_URL, dest: Path = DEFAULT_DEST_PATH) -> bool:
    """Download the GGUF model from HF to target path."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Target Destination: {dest.resolve()}")
    
    if dest.exists():
        # Check size to see if it's already downloaded (Qwen 1.5B GGUF is approx 1.13 GB)
        current_size = dest.stat().st_size
        print(f"File already exists with size: {format_size(current_size)}")
        if current_size > 1 * 1024 * 1024 * 1024:  # > 1GB
            print("Model appears to be fully downloaded. Skipping download.")
            return True
        else:
            print("File exists but size seems small/incomplete. Redownloading...")

    print(f"Source URL: {url}")
    print("This will download a ~1.2 GB model. Please make sure you have enough disk space and a stable network connection.")
    
    try:
        # Request headers to bypass potential user-agent blocks
        opener = urllib.request.build_opener()
        opener.addheaders = [("User-Agent", "SLM-Enterprise-Platform-Downloader/1.0")]
        urllib.request.install_opener(opener)
        
        # Start download
        urllib.request.urlretrieve(url, str(dest), reporthook=download_progress_hook)
        print("\n\nDownload completed successfully!")
        
        # Verify file exists
        if dest.exists():
            print(f"Model saved successfully to {dest.resolve()} (Size: {format_size(dest.stat().st_size)})")
            return True
        return False
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user. Cleaning up incomplete file...")
        if dest.exists():
            dest.unlink()
        return False
    except Exception as exc:
        print(f"\n\nError downloading model: {exc}")
        if dest.exists():
            dest.unlink()
        return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL_URL
    dest_str = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_DEST_PATH)
    
    success = download_model(url, Path(dest_str))
    sys.exit(0 if success else 1)
