"""
main.py — Orchestrates CLI commands by calling the underlying modules.
"""

import os
import json
from typing import List

from .shopify_utils.api import ShopifyAPI
from .shopify_utils.utils import log, sanitize, title_case
from .shopify_utils.media import MediaUploader
from .shopify_utils.metaobjects import MetaobjectManager
from .shopify_utils.collections import CollectionManager
from .shopify_utils.products import VariantUpdater
from .data_ingest.parser import ProductParser


# ---------- products.export ----------

def cmd_products_export(xlsx_path: str, template_csv: str, out_csv: str) -> None:
    pp = ProductParser(xlsx_path, template_csv, out_csv)
    df = pp.parse_excel()
    pp.to_csv()
    log(f"Exported {len(df)} rows → {out_csv}")


# ---------- recipes.publish ----------

def _collect_recipe_folders(root: str) -> List[str]:
    """
    Each child folder under root represents a recipe slug (folder name).
    We’ll upload images from each, then upsert a metaobject with title + up to 3 images.
    """
    folders = []
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath == root:
            for d in dirnames:
                folders.append(os.path.join(dirpath, d))
    return folders


def cmd_recipes_publish(root_images_dir: str) -> None:
    api = ShopifyAPI()
    mu = MediaUploader(api)
    mo = MetaobjectManager(api)

    for folder in _collect_recipe_folders(root_images_dir):
        folder_name = os.path.basename(folder)
        handle = {"type": "recipes", "handle": sanitize(folder_name)}
        title = title_case(folder_name)

        # Upload images in the folder
        image_ids: List[str] = []
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                file_path = os.path.join(folder, fn)
                file_id, _ = mu.upload_file(file_path)
                if file_id:
                    image_ids.append(file_id)

        # Prepare metaobject fields
        fields = [{"key": "title", "value": title}]
        for i, img_id in enumerate(image_ids[:3], start=1):
            fields.append({"key": f"image_{i}", "value": img_id})

        metaobject_data = {
            "fields": fields,
            "capabilities": {
                "onlineStore": {"templateSuffix": "recipes-template"},
                "publishable": {"status": "ACTIVE"},
            },
        }
        meta_id = mo.upsert_metaobject(handle, metaobject_data)
        log(f"Upserted recipe metaobject: {title} (id={meta_id})")


# ---------- blog.publish ----------

def cmd_blog_publish(blog_id: str) -> None:
    """
    For each recipe metaobject, generate blog HTML and create a blog article.
    This example assumes metaobject type 'recipes' and keys 'cocktail_history', 'ingredients', 'instructions' when present.
    """
    api = ShopifyAPI()
    mo = MetaobjectManager(api)

    # Fetch recent metaobjects by brute-force handle list (derived from files already uploaded earlier)
    # In practice, you might store known handles, or query via a custom index. Here we demo by reading images root.
    # To keep this cohesive without a DB, we just no-op if nothing found.
    log("blog.publish: This command expects recipe metaobjects already created by recipes.publish.")
    # If you want to enumerate, add a list of handles and loop mo.get_metaobject_by_handle(handle)

    log("Nothing to do automatically. Provide a handle list here if needed.")
    # (Left intentionally simple to avoid false assumptions about data source)


# ---------- variants.update ----------

def cmd_variants_update(what: str) -> None:
    """
    Fetch first 50 products with variants via GraphQL, then:
      - reorder variants
      - update metafields using parsed data (if available)
    """
    api = ShopifyAPI()
    vu = VariantUpdater(api=api)

    # We try to load parsed CSV if it exists to support metafields; otherwise, metafields step will no-op safely.
    parsed_csv = "assets/output_product_template_no_images.csv"
    if os.path.exists(parsed_csv):
        # attach a parser instance to VariantUpdater (for quantities)
        pp = ProductParser(
            excel_path="assets/DEHY_master_price_list_3.5.24.xlsx",
            csv_template_path="assets/products_export_06-25-2024.csv",
            output_csv_path=parsed_csv,
        )
        # If CSV already exists we don't need to regenerate; but we do need df.
        if pp.df.empty:
            # parse to populate df (no output write if not needed)
            pp.parse_excel()
        vu.parsed_df = pp.df

    # Pull products (first N = 50 for demo)
    query = """
    query {
      products(first: 50) {
        edges {
          node {
            id
            title
            variants(first: 50) {
              nodes {
                id
                title
                price
                selectedOptions { name value }
              }
            }
          }
        }
      }
    }
    """
    data = api.query(query)

    edges = (
        data.get("data", {})
        .get("products", {})
        .get("edges", [])
    )

    for edge in edges:
        product = edge["node"]
        product_id = product["id"]
        title = product["title"]
        variants_raw = product["variants"]["nodes"]

        # Normalize variants to include option1 name/value like Shopify REST
        variants = []
        for v in variants_raw:
            opt1 = next((o["value"] for o in v.get("selectedOptions", []) if o["name"] in ("Size", "Option1")), None)
            variants.append({
                "id": v["id"],
                "title": v["title"],
                "price": v["price"],
                "option1": opt1 or v["title"],  # fallback
            })

        if what in ("positions", "all"):
            vu._update_variant_positions(product_id, variants)

        if what in ("metafields", "all"):
            for v in variants:
                vu._update_variant_metafields(v, title)

    log("variants.update complete.")


# ---------- youtube.upload ----------

def cmd_youtube_upload(root_videos_dir: str, client_secrets_file: str) -> None:
    for folder in _collect_recipe_folders(root_videos_dir):
        vid = upload_video_and_sync(folder, client_secrets_file)
        if vid:
            log(f"YouTube synced: {vid}")