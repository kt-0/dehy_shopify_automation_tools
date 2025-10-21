"""
api.py — Core Shopify GraphQL client
"""

import os
import requests
import json
from typing import Any, Dict, Optional


class ShopifyAPI:
    """Simple wrapper for Shopify GraphQL requests with built-in error handling."""

    def __init__(self, shop_name: str = None, api_version: str = None):
        self.shop_name = shop_name or os.getenv("SHOPIFY_SHOP_NAME", "dehy-garnishes")
        self.api_version = api_version or os.getenv("SHOPIFY_API_VERSION", "2024-04")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")

        if not self.access_token:
            raise EnvironmentError("SHOPIFY_ACCESS_TOKEN not found in environment.")

        self.base_url = f"https://{self.shop_name}.myshopify.com/admin/api/{self.api_version}/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a GraphQL query or mutation to Shopify."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=60)
        try:
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                print("GraphQL errors:", json.dumps(data["errors"], indent=2))
            return data
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            print(f"Response: {response.text}")
            raise
        except json.JSONDecodeError:
            print("Invalid JSON response from Shopify.")
            raise
