"""
collections.py — Create or update Shopify collections and attach products.
"""

from typing import List, Dict, Optional
from .api import ShopifyAPI
from .utils import log, recursive_dict_search


class CollectionManager:
    """Manages creation, retrieval, and updating of Shopify collections."""

    def __init__(self, api: Optional[ShopifyAPI] = None):
        self.api = api or ShopifyAPI()

    def get_collection_by_handle(self, handle: str) -> Optional[Dict]:
        query = """
        query getCollectionByHandle($handle: String!) {
          collectionByHandle(handle: $handle) {
            id
            title
            products(first: 20, sortKey: BEST_SELLING) {
              edges { node { id title } }
            }
          }
        }
        """
        variables = {"handle": handle}
        result = self.api.query(query, variables)
        return recursive_dict_search(result, "collectionByHandle")

    def update_or_create_collection(self, title: str, product_ids: List[str]) -> Optional[str]:
        handle = title.strip().lower().replace(" ", "-")
        collection = self.get_collection_by_handle(handle)

        if collection:
            existing_ids = [e["node"]["id"] for e in collection["products"]["edges"]]
            new_ids = [pid for pid in product_ids if pid not in existing_ids]
            if not new_ids:
                log(f"No new products to add to collection '{title}'.")
                return collection["id"]

            mutation = """
            mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
              collectionAddProducts(id: $id, productIds: $productIds) {
                collection { id title }
                userErrors { field message }
              }
            }
            """
            variables = {"id": collection["id"], "productIds": new_ids}
            result = self.api.query(mutation, variables)
            return recursive_dict_search(result, "id")
        else:
            mutation = """
            mutation CollectionCreate($input: CollectionInput!) {
              collectionCreate(input: $input) {
                collection { id title handle }
                userErrors { field message }
              }
            }
            """
            variables = {"input": {"handle": handle, "title": title, "products": product_ids}}
            result = self.api.query(mutation, variables)
            return recursive_dict_search(result, "id")
