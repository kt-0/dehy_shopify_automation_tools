"""
transcriber.py — Extracts audio from cocktail recipe videos, transcribes using Whisper,
and refines structure with ChatGPT into structured recipe JSON.
"""

import os
import json
import moviepy.editor as mp
from openai import OpenAI


class CocktailRecipeTranscriber:
    """Converts cocktail videos into structured recipe data using Whisper + GPT."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

        self.PRODUCT_LIST = [
            "Apple - Fine Cut",
            "Blood Orange - Fine Cut",
            "Chrysanthemum Yellow - Hand Cut",
            "Citrus Jar Set",
            "Dragonfruit Red - Fine Cut",
            "Dragonfruit White - Fine Cut",
            "Figs - Hand Cut",
            "Grapefruit - Fine Cut",
            "Kiwifruit - Fine Cut",
            "Lapel Pin",
            "Lavender - Hand Cut",
            "Lemon - Fine Cut",
            "Lime - Fine Cut",
            "Lotus Root - Fine Cut",
            "Mini Clothespins",
            "Orange - Fine Cut",
            "Pear - Fine Cut",
            "Persimmon - Fine Cut",
            "Pineapple Half - Fine Cut",
            "Pineapple Whole - Fine Cut",
            "Roses - Hand Cut",
            "Sphinx Hat",
            "Star Fruit - Fine Cut",
            "Strawberries - Fine Cut",
        ]

        self.product_list_str = ", ".join(self.PRODUCT_LIST)

        self.PROMPT_GUIDE = (
            "The transcription is about a cocktail recipe and will be used alongside a video "
            "on a website that sells cocktail garnishes. The tone should be light and blog-style, "
            "but structured like a cooking recipe. Include a short intro (history, flavor, context), "
            "then a bulleted list of ingredients, and finally numbered instructions.\n\n"
            "Output a valid JSON object with these keys:\n"
            "  - cocktail_history (string)\n"
            "  - intro (string)\n"
            "  - ingredients (list of strings)\n"
            "  - instructions (list of strings)\n\n"
            f"Always reference these products exactly by name when relevant: {self.product_list_str}. "
            "Replace variations of 'Dehy' or 'Dehigh' with 'DEHY', the company name."
        )

        self.PROMPT_SUMMARY = (
            "This audio is a cocktail recipe narration. Include intro, ingredients, and instructions."
        )

    # --- AUDIO / VIDEO PROCESSING ---

    def extract_audio(self, video_file: str, output_audio_file: str):
        """Extract audio from a video file and save as .wav."""
        video = mp.VideoFileClip(video_file)
        video.audio.write_audiofile(output_audio_file, verbose=False, logger=None)

    def transcribe_audio(self, audio_file: str) -> str:
        """Transcribe audio using Whisper."""
        with open(audio_file, "rb") as audio:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                prompt=self.PROMPT_SUMMARY,
                language="en",
            )
        return transcription.text.strip()

    # --- TEXT PROCESSING ---

    def generate_corrected_transcript(self, audio_text: str) -> str:
        """Refine and structure the transcription via GPT."""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {"role": "system", "content": self.PROMPT_GUIDE},
                {"role": "user", "content": audio_text},
            ],
        )

        text = response.choices[0].message.content.strip()
        # Remove Markdown artifacts
        text = text.strip("` \n").replace("json\n", "").strip()
        return text

    def process_video(self, video_file: str):
        """End-to-end process: extract audio, transcribe, and structure output."""
        audio_file = f"{os.path.splitext(video_file)[0]}-audio.wav"

        self.extract_audio(video_file, audio_file)
        transcription = self.transcribe_audio(audio_file)
        corrected_json = self.generate_corrected_transcript(transcription)

        return transcription, corrected_json

    # --- VALIDATION ---

    def validate_response_structure(self, data: dict):
        """Ensure all required keys exist in the structured JSON."""
        required = {"cocktail_history", "ingredients", "intro", "instructions"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Missing keys in recipe output: {', '.join(missing)}")

    def parse_corrected_transcript(self, corrected_text: str) -> dict:
        """Parse JSON response from GPT and validate fields."""
        parsed = json.loads(corrected_text)
        self.validate_response_structure(parsed)
        return parsed
