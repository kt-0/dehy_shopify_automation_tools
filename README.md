# DEHY Shopify Automation Tools

Automates turning short cocktail videos into published recipe pages with linked products.

- Extract audio → transcribe (Whisper) → format JSON (GPT)
- Upload media → upsert Shopify metaobjects → publish blog articles
- Upload to YouTube and sync the video URL
- Parse Excel → export Shopify product CSV
- Update product variant order and metafields

---
## End-to-End Pipeline
```
[ Videos ]              [ Images ]                [ Excel / Shopify CSVs ]
     |                        |                               |
     v                        v                               v
[ Audio Extract ]    [ Resize / Rename ]              [ Data Parser ]
     |                        |                               |
     v                        v                               v
[ Whisper Text ]      [ Media Upload ]               [ Shopify CSV ]
     |                        |                               |
     v                        v                               v
[ GPT JSON   ]  --> [ Shopify Metaobject ] <--> [ Variant / Metafield Sync ]
     |                        |
     |                        v
     |                [ Blog Article (HTML) ]
     |                        |
     v                        v
[ YouTube Upload ] -> [ Metaobject updated with links ]
            \_____________________  _____________________/
                                  \/
                           [ Published Recipe ]
```
---

## Project Structure
```
dehy_shopify_automation_tools/
├─ src/
│  ├─ shopify_utils/
│  │  ├─ __init__.py
│  │  ├─ api.py            # Shopify GraphQL client
│  │  ├─ utils.py          # helpers (sanitize, logging, etc.)
│  │  ├─ metaobjects.py    # recipe metaobject upsert/get, build blog HTML
│  │  ├─ media.py          # staged uploads (image/video)
│  │  ├─ collections.py    # ensure collection + add products
│  │  └─ products.py       # variant ordering + metafields
│  ├─ data_ingest/
│  │  ├─ __init__.py
│  │  ├─ parser.py         # Excel → DataFrame → Shopify CSV fields
│  │  └─ validator.py      # (optional) schema checks
│  ├─ transcription/
│  │  ├─ __init__.py
│  │  ├─ transcriber.py    # moviepy extract → Whisper
│  │  └─ formatter.py      # GPT formatting to strict JSON
│  ├─ media_processing/
│  │  ├─ __init__.py
│  │  ├─ image_tools.py    # resize / rename
│  │  └─ video_tools.py    # (optional) trim / normalize
│  ├─ cli.py               # argparse entrypoints
│  └─ main.py              # workflow orchestration
│
├─ assets/
│  ├─ DEHY_master_price_list_3.5.24.xlsx
│  ├─ products_export_06-25-2024.csv
│  └─ output_product_template_no_images.csv
├─ media/
│  ├─ images/
│  │  └─ cocktail_recipes/...
│  └─ videos/
│     └─ cocktail_recipes/...
├─ .env.example
├─ requirements.txt
├─ README.md
└─ LICENSE
```
---

## Setup

1) Install dependencies
$ pip install -r requirements.txt

2) Configure environment
$ cp .env.example .env
Add required API keys and IDs.

3) Place inputs
- Excel/CSVs in `assets/`
- Images/videos in `media/`

---

## Commands

All commands run via `src/cli.py` → `src/main.py`.

Parse Excel and create a Shopify-ready product CSV
$ python -m src.cli products.export \
  --xlsx assets/DEHY_master_price_list_3.5.24.xlsx \
  --template assets/products_export_06-25-2024.csv \
  --out assets/output_product_template_no_images.csv

Upload recipe media and upsert metaobjects
$ python -m src.cli recipes.publish --root media/images/cocktail_recipes

Create blog articles from recipe metaobjects
$ python -m src.cli blog.publish --blog-id gid://shopify/Blog/82488656028

Update variant positions and metafields
$ python -m src.cli variants.update --what all

---

## Notes

- Metaobjects of type `recipes` store title, images, and related content.
- Blog bodies are generated from metaobject fields as semantic HTML.
- Media uses Shopify staged uploads; files are finalized and referenced by ID.
- Variant ordering/metafields (e.g., quantity, price-per-piece) are applied via GraphQL.

---

## License

MIT (include a LICENSE file if open-sourcing).
