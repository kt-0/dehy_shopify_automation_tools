"""
parser.py — Parse DEHY Excel sheets into a normalized DataFrame
and produce a Shopify-ready product CSV using a template.
"""

import math
import re
import pandas as pd
from typing import List
from ..shopify_utils.utils import log


class ProductParser:
    def __init__(self, excel_path: str, csv_template_path: str, output_csv_path: str):
        self.excel_path = excel_path
        self.csv_template_path = csv_template_path
        self.output_csv_path = output_csv_path
        self.size_list = ["Large Bulk", "Small Bulk", "Hanging Pouch", "Stand Up Pouch", "Small Jar", "Large Jar"]
        self.cut_list = ["Fine Cut", "Hand Cut"]
        self.df = pd.DataFrame()

    @staticmethod
    def _calc_avg_quantity(cell: str) -> int:
        cell = str(cell).replace("pc", "")
        if "-" in cell:
            vals = [int(x.strip()) for x in cell.split("-")]
            return math.ceil(sum(vals) / len(vals))
        return int(cell)

    @staticmethod
    def _sanitize(s: str) -> str:
        return s.strip().replace(" ", "_").lower()

    def parse_excel(self) -> pd.DataFrame:
        with pd.ExcelFile(self.excel_path) as wb:
            parsed = []
            for name in wb.sheet_names:
                if name not in ["Wholesale", "Retail"]:
                    continue
                df = wb.parse(name, header=None)
                df.columns = ["SKU", "UPC", "PRODUCT", "WEIGHT", "QUANTITY", "RETAIL_PRICE", "UNIT_PRICE"][: len(df.columns)]
                df["QUANTITY"] = df["QUANTITY"].apply(self._calc_avg_quantity)
                for _, row in df.iterrows():
                    product = str(row["PRODUCT"])
                    product_name = re.split(r" - |_", product)[0].strip()
                    cut = next((c for c in self.cut_list if c in product), "")
                    size = next((s for s in self.size_list if s in product), "")
                    parsed.append(
                        {
                            "SKU": row["SKU"],
                            "UPC": row["UPC"],
                            "PRODUCT": product_name,
                            "PRODUCT_TITLE": f"{product_name} - {cut}",
                            "VARIANT_SIZE": size,
                            "WEIGHT": row["WEIGHT"],
                            "QUANTITY": row["QUANTITY"],
                            "RETAIL_PRICE": row["RETAIL_PRICE"],
                            "UNIT_PRICE": row["UNIT_PRICE"],
                            "HANDLE": f"dehydrated_{self._sanitize(product_name)}_cocktail_garnish",
                        }
                    )
        self.df = pd.DataFrame(parsed)
        log(f"Parsed {len(self.df)} rows from Excel.")
        return self.df

    def to_csv(self) -> None:
        csv_template = pd.read_csv(self.csv_template_path)
        rows = []
        for _, r in self.df.iterrows():
            row = csv_template.iloc[0].copy()
            row["Handle"] = r["HANDLE"]
            row["Title"] = r["PRODUCT_TITLE"]
            row["Option1 Name"] = "Size"
            row["Option1 Value"] = r["VARIANT_SIZE"]
            row["Variant Price"] = r["RETAIL_PRICE"]
            row["Variant SKU"] = r["SKU"]
            row["Variant Weight Unit"] = "g"
            row["Variant Grams"] = str(r["WEIGHT"]).replace("g", "").strip()
            row["Variant Requires Shipping"] = "TRUE"
            row["Variant Inventory Policy"] = "deny"
            row["Variant Taxable"] = "TRUE"
            rows.append(row)
        out = pd.DataFrame(rows)
        out.to_csv(self.output_csv_path, index=False)
        log(f"Wrote CSV: {self.output_csv_path}")
