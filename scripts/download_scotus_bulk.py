#!/usr/bin/env python3
"""
Script to bulk download all US Supreme Court opinions from Court Listener.

This script downloads the complete SCOTUS opinions dataset as a tar.gz file
and extracts it to a local directory for processing.
"""

import sys
from pathlib import Path
from typing import Optional
import requests
import tarfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def download_scotus_bulk(
    output_dir: str = "raw-data/scotus_data",
    download_file: str = "scotus_opinions.tar.gz"
) -> bool:
    """Download and extract the bulk SCOTUS opinions dataset.
    
    Args:
        output_dir: Directory to extract the data to
        download_file: Name of the downloaded tar.gz file
        
    Returns:
        True if successful, False otherwise
    """
    url = "https://www.courtlistener.com/api/bulk-data/opinions/scotus.tar.gz"
    
    try:
        print(f"Starting download from {url}")
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Download with progress tracking
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        download_path = Path(download_file)
        with open(download_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"Downloaded: {percent:.1f}%", end='\r')
        
        print(f"\nDownload complete! File saved as {download_path}")
        
        # Extract the archive
        print(f"Extracting to {output_path}/")
        with tarfile.open(download_path, "r:gz") as tar:
            tar.extractall(output_path)
        
        print("Extraction complete!")
        
        # Optionally remove the tar.gz file to save space
        # download_path.unlink()
        
        return True
        
    except requests.RequestException as e:
        print(f"Error downloading file: {e}", file=sys.stderr)
        return False
    except tarfile.TarError as e:
        print(f"Error extracting archive: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False


def main() -> None:
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download bulk SCOTUS opinions from Court Listener"
    )
    parser.add_argument(
        "--output-dir",
        default="raw-data/scotus_data",
        help="Output directory for extracted data (default: raw-data/scotus_data)"
    )
    parser.add_argument(
        "--download-file",
        default="scotus_opinions.tar.gz",
        help="Name for downloaded file (default: scotus_opinions.tar.gz)"
    )
    
    args = parser.parse_args()
    
    success = download_scotus_bulk(
        output_dir=args.output_dir,
        download_file=args.download_file
    )
    
    if not success:
        sys.exit(1)
    
    print(f"All SCOTUS opinions successfully downloaded to {args.output_dir}/")


if __name__ == "__main__":
    main()