"""
cli.py — Command-line entrypoints.
Usage examples (run from repo root):
  python -m src.cli products.export --xlsx assets/DEHY_master_price_list_3.5.24.xlsx --template assets/products_export_06-25-2024.csv --out assets/output_product_template_no_images.csv
  python -m src.cli recipes.publish --root media/images/cocktail_recipes
  python -m src.cli blog.publish --blog-id gid://shopify/Blog/82488656028
  python -m src.cli variants.update --what all
"""

import argparse
from .main import (
    cmd_products_export,
    cmd_recipes_publish,
    cmd_blog_publish,
    cmd_variants_update,
)


def main():
    parser = argparse.ArgumentParser(prog="dehy_shopify_automation_tools")
    sub = parser.add_subparsers(dest="command", required=True)

    # products.export
    p_export = sub.add_parser("products.export", help="Parse Excel and export a Shopify-ready CSV")
    p_export.add_argument("--xlsx", required=True)
    p_export.add_argument("--template", required=True)
    p_export.add_argument("--out", required=True)

    # recipes.publish
    r_pub = sub.add_parser("recipes.publish", help="Upload images and upsert recipe metaobjects")
    r_pub.add_argument("--root", required=True, help="Root folder containing recipe image subfolders")

    # blog.publish
    b_pub = sub.add_parser("blog.publish", help="Create blog articles from recipe metaobjects")
    b_pub.add_argument("--blog-id", required=True, help="gid://shopify/Blog/<id>")

    # variants.update
    v_upd = sub.add_parser("variants.update", help="Update variant positions and metafields")
    v_upd.add_argument("--what", choices=["positions", "metafields", "all"], default="all")

    args = parser.parse_args()

    if args.command == "products.export":
        cmd_products_export(args.xlsx, args.template, args.out)

    elif args.command == "recipes.publish":
        cmd_recipes_publish(args.root)

    elif args.command == "blog.publish":
        cmd_blog_publish(args.blog_id)

    elif args.command == "variants.update":
        cmd_variants_update(args.what)


if __name__ == "__main__":
    main()
