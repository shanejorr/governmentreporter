#!/usr/bin/env python3
"""
Federal Register Executive Orders Fetcher

This script fetches all executive orders from a given date to the present
using the Federal Register API and saves the data to output.json.

Usage:
    python fetch_executive_orders.py --start-date 2020-01-01
"""

import argparse
import json
import time
from datetime import date, datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests


class FederalRegisterClient:
    """Client for interacting with the Federal Register API"""

    BASE_URL = "https://www.federalregister.gov/api/v1"

    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize the client

        Args:
            rate_limit_delay: Delay between API requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        # Set a proper User-Agent
        self.session.headers.update(
            {"User-Agent": "GovernmentReporter/1.0 (Educational/Research Project)"}
        )

    def get_executive_orders(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        include_full_text: bool = False,
    ) -> List[Dict]:
        """
        Fetch all executive orders from start_date to present

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to today)
            include_full_text: Whether to fetch full text content for each order

        Returns:
            List of executive order documents
        """
        if end_date is None:
            end_date = date.today().isoformat()

        print(f"Fetching executive orders from {start_date} to {end_date}...")

        all_orders = []
        page = 1
        total_pages = None

        while True:
            # Build query parameters
            params = {
                "conditions[type]": "PRESDOCU",
                "conditions[presidential_document_type]": "executive_order",
                "conditions[publication_date][gte]": start_date,
                "conditions[publication_date][lte]": end_date,
                "conditions[correction]": "0",  # Exclude corrections
                "per_page": "1000",  # Maximum allowed
                "page": str(page),
                "order": "oldest",  # Start with oldest first
                # Specify fields to return
                "fields[]": [
                    "document_number",
                    "title",
                    "executive_order_number",
                    "publication_date",
                    "signing_date",
                    "president",
                    "citation",
                    "html_url",
                    "pdf_url",
                    "full_text_xml_url",
                    "body_html_url",
                    "raw_text_url",
                    "json_url",
                ],
            }

            # Federal Register API expects multiple fields[] parameters
            url = f"{self.BASE_URL}/articles.json"

            # Build URL manually to handle multiple fields[] parameters
            field_params = "&".join(
                [f"fields[]={field}" for field in params["fields[]"]]
            )
            del params["fields[]"]

            base_params = urlencode(params)
            full_url = f"{url}?{base_params}&{field_params}"

            print(
                f"Fetching page {page}{'/' + str(total_pages) if total_pages else ''}..."
            )

            try:
                response = self.session.get(full_url)
                response.raise_for_status()
                data = response.json()

                if total_pages is None:
                    total_pages = data.get("total_pages", 1)
                    print(
                        f"Found {data.get('count', 0)} total executive orders across {total_pages} pages"
                    )

                results = data.get("results", [])

                if not results:
                    break

                # Optionally fetch full text for each order
                if include_full_text:
                    results = self._fetch_full_text_for_orders(results)

                all_orders.extend(results)

                print(f"Retrieved {len(results)} orders from page {page}")

                # Check if we've reached the end
                if page >= total_pages or page >= 2:  # API pagination limit
                    break

                page += 1

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            except requests.RequestException as e:
                print(f"Error fetching page {page}: {e}")
                break

        print(f"Total executive orders retrieved: {len(all_orders)}")
        return all_orders

    def _fetch_full_text_for_orders(self, orders: List[Dict]) -> List[Dict]:
        """
        Fetch full text content for each executive order

        Args:
            orders: List of order metadata dictionaries

        Returns:
            List of orders with full_text added
        """
        print("Fetching full text content for orders...")

        for i, order in enumerate(orders):
            # Try different URL sources in order of preference
            text_urls = [
                order.get("raw_text_url"),
                order.get("body_html_url"),
                order.get("full_text_xml_url"),
            ]

            full_text = None
            for url in text_urls:
                if url:
                    full_text = self._fetch_text_content(url)
                    if full_text:
                        break

            if full_text:
                order["full_text"] = full_text
                print(
                    f"  [{i+1}/{len(orders)}] Retrieved text for EO {order.get('executive_order_number', 'Unknown')}"
                )
            else:
                print(
                    f"  [{i+1}/{len(orders)}] Failed to retrieve text for EO {order.get('executive_order_number', 'Unknown')}"
                )

            # Rate limiting for full text requests
            time.sleep(self.rate_limit_delay)

        return orders

    def _fetch_text_content(self, url: str) -> Optional[str]:
        """
        Fetch text content from a URL

        Args:
            url: URL to fetch content from

        Returns:
            Text content or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Handle different content types
            content_type = response.headers.get("content-type", "").lower()

            if "html" in content_type:
                # For HTML, you might want to extract just the text content
                # This is a simple approach - you might want to use BeautifulSoup for better parsing
                return response.text
            else:
                # Assume plain text
                return response.text

        except requests.RequestException as e:
            print(f"    Error fetching text from {url}: {e}")
            return None


def save_to_json(data: List[Dict], filename: str = "output.json"):
    """
    Save data to JSON file

    Args:
        data: Data to save
        filename: Output filename
    """
    print(f"Saving {len(data)} records to {filename}...")

    # Create output structure
    output = {
        "metadata": {
            "total_records": len(data),
            "fetched_at": datetime.now().isoformat(),
            "source": "Federal Register API v1",
            "document_type": "executive_orders",
        },
        "executive_orders": data,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Successfully saved to {filename}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Fetch executive orders from Federal Register API"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date in YYYY-MM-DD format (e.g., 2020-01-01)",
    )
    parser.add_argument(
        "--end-date", help="End date in YYYY-MM-DD format (defaults to today)"
    )
    parser.add_argument(
        "--include-full-text",
        action="store_true",
        help="Fetch full text content for each executive order (slower but more complete)",
    )
    parser.add_argument(
        "--output", default="output.json", help="Output filename (default: output.json)"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Delay between API requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return

    # Create client and fetch data
    client = FederalRegisterClient(rate_limit_delay=args.rate_limit)

    try:
        orders = client.get_executive_orders(
            start_date=args.start_date,
            end_date=args.end_date,
            include_full_text=args.include_full_text,
        )

        if orders:
            save_to_json(orders, args.output)
        else:
            print("No executive orders found for the specified date range.")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
