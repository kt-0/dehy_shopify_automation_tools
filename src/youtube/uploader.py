"""
uploader.py — Upload recipe videos to YouTube and sync the video URL to the recipe metaobject.
"""

import os
import json
from typing import Optional, Dict, List

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..shopify_utils.utils import log, title_case, sanitize
from ..shopify_utils.metaobjects import MetaobjectManager


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _format_rich_list(json_data: str) -> str:
    """Convert Shopify RichText JSON to a plain-text bullet/numbered list."""
    try:
        data = json.loads(json_data)
    except Exception:
        return ""
    items = data.get("children", [{}])[0].get("children", [])
    list_type = data.get("children", [{}])[0].get("listType", "unordered")
    lines = []
    for i, item in enumerate(items, 1):
        parts = []
        for child in item.get("children", []):
            if child.get("type") == "text":
                parts.append(child.get("value", ""))
            elif child.get("type") == "link":
                text = "".join(c.get("value", "") for c in child.get("children", []) if c.get("type") == "text")
                title = child.get("title") or ""
                parts.append(f"{title}: {text}" if title else text)
        line = "".join(parts).strip()
        if not line:
            continue
        lines.append(f"{i}. {line}" if list_type == "ordered" else f"• {line}")
    return "\n".join(lines)


def _video_description_from_meta(meta: Dict) -> str:
    fields = {f["key"]: f["value"] for f in meta.get("fields", [])}
    intro = fields.get("intro", "")
    history = fields.get("cocktail_history", "")
    ingredients = _format_rich_list(fields.get("ingredients", "") or "")
    instructions = _format_rich_list(fields.get("instructions", "") or "")
    sections = [
        history.strip(),
        intro.strip(),
        "Ingredients:\n" + ingredients if ingredients else "",
        "Instructions:\n" + instructions if instructions else "",
    ]
    return "\n\n".join([s for s in sections if s]).strip()


def _youtube(credentials, title: str):
    yt = build("youtube", "v3", credentials=credentials)
    # Simple existence check by title
    req = yt.search().list(part="snippet", forMine=True, type="video", q=title, maxResults=50)
    res = req.execute()
    for item in res.get("items", []):
        if item["snippet"]["title"].strip().lower() == title.strip().lower():
            return yt, item["id"]["videoId"]
    return yt, None


def upload_video_and_sync(
    folder_path: str,
    client_secrets_file: str,
    blog_tags: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Upload first video found in folder_path to YouTube, then write URL back to recipe metaobject.
    Returns the YouTube video ID if created/found.
    """
    blog_tags = blog_tags or ["cocktail", "recipe", "dehy", "dehygarnish"]

    # OAuth
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    credentials = flow.run_local_server(port=0)

    folder_name = os.path.basename(folder_path)
    title = title_case(folder_name)

    # Find a video file
    video_file = next((f for f in os.listdir(folder_path) if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))), None)
    if not video_file:
        log(f"No video found in {folder_path}")
        return None

    video_path = os.path.join(folder_path, video_file)

    # Fetch metaobject (for description + later URL sync)
    mo = MetaobjectManager()
    handle = {"type": "recipes", "handle": sanitize(folder_name)}
    meta = mo.get_metaobject_by_handle(handle)
    description = _video_description_from_meta(meta or {"fields": []})

    yt, existing_id = _youtube(credentials, title)
    if existing_id:
        log(f"YouTube video already exists: {existing_id}")
        video_id = existing_id
    else:
        body = {
            "snippet": {"title": title, "description": description, "tags": blog_tags, "categoryId": "22"},
            "status": {"privacyStatus": "public"},
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        res = req.execute()
        video_id = res["id"]
        log(f"Uploaded YouTube video: {video_id}")

    # Sync back to metaobject (add/update 'video_url')
    meta_fields = [{"key": "title", "value": title}, {"key": "video_url", "value": f"https://www.youtube.com/watch?v={video_id}"}]
    mo.upsert_metaobject(handle, {"fields": meta_fields})

    return video_id
