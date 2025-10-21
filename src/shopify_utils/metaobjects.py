"""
metaobjects.py — Create, update, and read Shopify metaobjects.
Also handles HTML generation for blog articles derived from metaobject data.
"""

import json
from typing import Dict, List, Any, Optional
from .api import ShopifyAPI
from .utils import log, pretty_json, recursive_dict_search


class MetaobjectManager:
    """Manages Shopify metaobjects for recipes, including creation and blog conversion."""

    def __init__(self, api: Optional[ShopifyAPI] = None):
        self.api = api or ShopifyAPI()

    def upsert_metaobject(self, handle: Dict[str, str], metaobject_data: Dict[str, Any]) -> Optional[str]:
        """Create or update a metaobject and return its ID."""
        mutation = """
        mutation UpsertMetaobject($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
            metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
                metaobject {
                    id
                    handle
                    fields { key value }
                }
                userErrors { field message code }
            }
        }
        """
        variables = {"handle": handle, "metaobject": metaobject_data}
        result = self.api.query(mutation, variables)
        log(f"Upsert metaobject result: {pretty_json(result)}")
        metaobject = recursive_dict_search(result, "metaobject")
        return metaobject.get("id") if metaobject else None

    def get_metaobject_by_handle(self, handle: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Fetch a metaobject by handle."""
        query = """
        query($handle: MetaobjectHandleInput!) {
            metaobjectByHandle(handle: $handle) {
                handle
                fields { key value }
            }
        }
        """
        variables = {"handle": handle}
        result = self.api.query(query, variables)
        metaobject = recursive_dict_search(result, "metaobjectByHandle")
        log(f"Metaobject fetched: {pretty_json(metaobject)}")
        return metaobject

    def generate_blog_html(self, metaobject: Dict[str, Any]) -> str:
        """Convert metaobject JSON fields into formatted HTML."""
        def extract_field(key: str) -> Optional[str]:
            for f in metaobject.get("fields", []):
                if f["key"] == key:
                    return f["value"]
            return None

        cocktail_history = extract_field("cocktail_history")
        ingredients_json = extract_field("ingredients")
        instructions_json = extract_field("instructions")

        html_output = ""

        if cocktail_history:
            html_output += f"<h4>Cocktail History</h4><p>{cocktail_history}</p>\n"

        if ingredients_json:
            ingredients = json.loads(ingredients_json)
            html_output += "<h4>Ingredients</h4><ul>\n"
            for item in ingredients["children"][0]["children"]:
                html_output += "<li>"
                for child in item["children"]:
                    if child["type"] == "text":
                        html_output += child["value"]
                    elif child["type"] == "link":
                        text = child["children"][0]["value"]
                        html_output += f'<a href="{child["url"]}" title="{child["title"]}">{text}</a>'
                html_output += "</li>\n"
            html_output += "</ul>\n"

        if instructions_json:
            instructions = json.loads(instructions_json)
            html_output += "<h4>Instructions</h4><ol>\n"
            for step in instructions["children"][0]["children"]:
                html_output += "<li>"
                for child in step["children"]:
                    if child["type"] == "text":
                        html_output += child["value"]
                    elif child["type"] == "link":
                        text = child["children"][0]["value"]
                        html_output += f'<a href="{child["url"]}" title="{child["title"]}">{text}</a>'
                html_output += "</li>\n"
            html_output += "</ol>\n"

        return html_output
