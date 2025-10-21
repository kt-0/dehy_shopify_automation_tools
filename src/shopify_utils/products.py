"""
products.py — Shopify variant updates (ordering + metafields).
"""

import json
import pandas as pd
from typing import Dict, List, Optional
from .api import ShopifyAPI
from .utils import log


class VariantUpdater:
    """Updates Shopify variants’ positions and metafields."""

    VARIANT_ORDER = {"Pouch": 1, "Small Jar": 2, "Large Jar": 3, "Small Bulk": 4, "Large Bulk": 5}

    def __init__(self, api: Optional[ShopifyAPI] = None):
        self.api = api or ShopifyAPI()
        self.parsed_df = pd.DataFrame()  # to be set by caller if available

    def _update_variant_positions(self, product_id: str, variants: List[Dict]):
        mutation = """
        mutation ReorderVariants($productId: ID!, $positions: [ProductVariantPositionInput!]!) {
          productVariantsBulkReorder(productId: $productId, positions: $positions) {
            product { id title variants(first: 10) { nodes { id position } } }
            userErrors { code field message }
          }
        }
        """
        positions = []
        for v in variants:
            pos = self.VARIANT_ORDER.get(v.get("option1"))
            if pos:
                positions.append({"id": v["id"], "position": pos})
        if not positions:
            log("No variants matched known sizes for reordering.")
            return
        result = self.api.query(mutation, {"productId": product_id, "positions": positions})
        log(f"Variant positions updated: {json.dumps(result, indent=2)}")

    def _update_variant_metafields(self, variant: Dict, product_title: str):
        if self.parsed_df.empty:
            log("Parsed DataFrame empty; skip metafields.")
            return
        size = variant.get("option1")
        qty = self.parsed_df.loc[
            (self.parsed_df["PRODUCT_TITLE"] == product_title) & (self.parsed_df["VARIANT_SIZE"] == size),
            "QUANTITY",
        ]
        if qty.empty:
            log(f"No quantity found for {product_title} — {size}")
            return

        qty_val = int(qty.values[0])
        price_per_piece = {"amount": float(variant["price"]) / qty_val, "currency_code": "USD"}

        mutation = """
        mutation UpdateVariant($input: ProductVariantInput!) {
          productVariantUpdate(input: $input) {
            productVariant { id }
            userErrors { message field }
          }
        }
        """
        variables = {
            "input": {
                "id": variant["id"],
                "metafields": [
                    {"namespace": "custom", "key": "quantity", "type": "number_integer", "value": str(qty_val)},
                    {"namespace": "custom", "key": "price_per_piece", "type": "money", "value": json.dumps(price_per_piece)},
                ],
            }
        }
        result = self.api.query(mutation, variables)
        log(f"Variant metafields updated: {json.dumps(result, indent=2)}")
