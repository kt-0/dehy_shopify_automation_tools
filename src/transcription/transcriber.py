"""
transcriber.py — Extract audio from cocktail recipe videos, transcribe with Whisper,
and structure via GPT using your original PROMPT_GUIDE (unchanged).
"""

import os
import json
import moviepy.editor as mp
from openai import OpenAI


class CocktailRecipeTranscriber:
    """Converts cocktail videos into structured recipe data using Whisper + GPT."""

    def __init__(self, api_key: str | None = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.PRODUCT_LIST = [
            "Apple - Fine Cut", "Blood Orange - Fine Cut", "Chrysanthemum Yellow - Hand Cut",
            "Citrus Jar Set", "Dragonfruit Red - Fine Cut", "Dragonfruit White - Fine Cut",
            "Figs - Hand Cut", "Grapefruit - Fine Cut", "Kiwifruit - Fine Cut", "Lapel Pin",
            "Lavender - Hand Cut", "Lemon - Fine Cut", "Lime - Fine Cut", "Lotus Root - Fine Cut",
            "Mini Clothespins", "Orange - Fine Cut", "Pear - Fine Cut", "Persimmon - Fine Cut",
            "Pineapple Half - Fine Cut", "Pineapple Whole - Fine Cut", "Roses - Hand Cut",
            "Sphinx Hat", "Star Fruit - Fine Cut", "Strawberries - Fine Cut"
        ]
        self.product_list_str = ", ".join(self.PRODUCT_LIST)

        # === YOUR ORIGINAL PROMPT (unchanged) ===
        self.PROMPT_GUIDE = (
            "The transcription is about a cocktail recipe and will be used alongside a video"
            " on a website which sells cocktail garnishes. The format should be blog-esque in spirit, but follow"
            " a similar structure of a cooking recipe. A brief intro (history, flavor profile, etc.),"
            " followed by a bulleted ingredient list, and then a numbered instructions list. Don't include the actual numbers."
            " Please format the response as a JSON object with the following keys: 'cocktail_history', 'ingredients', 'intro', and 'instructions'."
            " The 'cocktail_history' should be a string, 'intro' should be a string, 'ingredients' should be a list of strings, and 'instructions' should be a list of strings."
            " Also, 'Dehigh', 'Dehi', etc. should be coerced to 'DEHY', as that is the company name."
            f" Make sure to properly reference our products with their exact names: {self.product_list_str}."
        )
        self.PROMPT_SUMMARY = "This is a cocktail recipe transcription. It has the following sections: Intro, Ingredient list, and instruction list. Company name is 'DEHY'"

    # --- AUDIO / VIDEO ---

    def extract_audio(self, video_file: str, output_audio_file: str):
        clip = mp.VideoFileClip(video_file)
        clip.audio.write_audiofile(output_audio_file, verbose=False, logger=None)

    def transcribe_audio(self, audio_file: str) -> str:
        with open(audio_file, "rb") as audio:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                prompt=self.PROMPT_SUMMARY,
                language="en",
            )
        return transcription.text.strip()

    # --- GPT STRUCTURING ---

    def generate_corrected_transcript(self, audio_text: str) -> str:
        """Return raw JSON text (no code fences), following PROMPT_GUIDE."""
        resp = self.client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            messages=[
                {"role": "system", "content": self.PROMPT_GUIDE},
                {"role": "user", "content": audio_text},
            ],
        )
        out = resp.choices[0].message.content.strip()
        out = out.strip("` \n")
        if out.lower().startswith("json"):
            out = out[4:].strip()
        return out

    def process_video(self, video_file: str):
        """Extract → transcribe → structure. Returns (raw_transcript, json_text)."""
        audio_file = f"{os.path.splitext(video_file)[0]}-audio.wav"
        self.extract_audio(video_file, audio_file)
        transcription = self.transcribe_audio(audio_file)
        corrected_json_text = self.generate_corrected_transcript(transcription)
        return transcription, corrected_json_text

    # --- VALIDATION/PARSING ---

    @staticmethod
    def validate_response_structure(d: dict):
        req = {"cocktail_history", "ingredients", "intro", "instructions"}
        missing = req - set(d.keys())
        if missing:
            raise ValueError(f"Missing keys: {', '.join(sorted(missing))}")
        if not isinstance(d["ingredients"], list) or not all(isinstance(x, str) for x in d["ingredients"]):
            raise ValueError("ingredients must be a list of strings")
        if not isinstance(d["instructions"], list) or not all(isinstance(x, str) for x in d["instructions"]):
            raise ValueError("instructions must be a list of strings")

    def process_corrected_transcript(self, corrected_transcript: str) -> dict:
        d = json.loads(corrected_transcript)
        self.validate_response_structure(d)
        return d
