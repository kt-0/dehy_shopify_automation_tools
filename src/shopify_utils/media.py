"""
media.py — Handles upload of images and videos to Shopify via staged uploads.
"""

import os
import requests
from typing import Dict, Tuple, Optional
from .api import ShopifyAPI
from .utils import log


class MediaUploader:
    """Upload media assets to Shopify (images/videos) using staged uploads."""

    def __init__(self, api: Optional[ShopifyAPI] = None):
        self.api = api or ShopifyAPI()

    def _get_content_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        if ext == ".png":
            return "image/png"
        if ext == ".gif":
            return "image/gif"
        if ext == ".mp4":
            return "video/mp4"
        return "application/octet-stream"

    def _create_staged_upload(self, file_path: str) -> Dict:
        file_name = os.path.basename(file_path)
        mime_type = self._get_content_type(file_path)
        file_size = os.path.getsize(file_path)
        resource = "VIDEO" if mime_type == "video/mp4" else "IMAGE"

        mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters { name value }
            }
          }
        }
        """
        variables = {
            "input": [
                {
                    "resource": resource,
                    "filename": file_name,
                    "mimeType": mime_type,
                    "httpMethod": "POST",
                    "fileSize": str(file_size),
                }
            ]
        }
        result = self.api.query(mutation, variables)
        return result["data"]["stagedUploadsCreate"]["stagedTargets"][0]

    def _upload_to_staged_target(self, staged_target: Dict, file_path: str) -> str:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {p["name"]: p["value"] for p in staged_target["parameters"]}
            response = requests.post(staged_target["url"], data=data, files=files, timeout=600)
            response.raise_for_status()
        return staged_target["resourceUrl"]

    def _finalize_upload(self, resource_url: str, file_name: str) -> Optional[str]:
        content_type = "VIDEO" if file_name.lower().endswith(".mp4") else "IMAGE"
        mutation = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files { id alt createdAt }
            userErrors { field message }
          }
        }
        """
        variables = {
            "files": [
                {
                    "filename": file_name,
                    "alt": file_name,
                    "originalSource": resource_url,
                    "contentType": content_type,
                    "duplicateResolutionMode": "REPLACE",
                }
            ]
        }
        result = self.api.query(mutation, variables)
        files = result["data"]["fileCreate"]["files"]
        return files[0]["id"] if files else None

    def upload_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Complete staged upload for a file (image or video)."""
        try:
            staged_target = self._create_staged_upload(file_path)
            resource_url = self._upload_to_staged_target(staged_target, file_path)
            file_id = self._finalize_upload(resource_url, os.path.basename(file_path))
            log(f"Uploaded: {file_path} (id={file_id})")
            return file_id, resource_url
        except Exception as e:
            log(f"Upload failed for {file_path}: {e}")
            return None, None
