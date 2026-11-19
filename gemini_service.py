import os
import time
import json
import requests
from typing import Dict, Any, List, Optional

BASE_URL = "https://generativelanguage.googleapis.com"

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def upload_file(self, file_path: str, mime_type: str = "audio/mp3") -> Dict[str, Any]:
        """
        Uploads a media file (audio or video) to the Gemini File API via Resumable Upload.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please provide a valid Gemini API Key.")

        file_size = os.path.getsize(file_path)
        display_name = os.path.basename(file_path)

        # Step 1: Initiate resumable upload
        init_url = f"{BASE_URL}/upload/v1beta/files?key={self.api_key}"
        init_headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        }
        init_body = json.dumps({"file": {"display_name": display_name}})

        init_resp = requests.post(init_url, headers=init_headers, data=init_body, timeout=60)
        if init_resp.status_code != 200:
            raise RuntimeError(f"Failed to initiate file upload to Gemini: {init_resp.status_code} - {init_resp.text}")

        upload_url = init_resp.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise RuntimeError("Gemini did not return an upload URL header.")

        # Step 2: Upload file bytes
        upload_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }

        with open(file_path, "rb") as f:
            upload_resp = requests.post(upload_url, headers=upload_headers, data=f, timeout=300)

        if upload_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to upload file content to Gemini: {upload_resp.status_code} - {upload_resp.text}")

        file_info = upload_resp.json().get("file", {})
        file_name = file_info.get("name")  # e.g., "files/abc123xyz"

        # Step 3: Wait for file to become ACTIVE
        self._wait_for_active(file_name)
        return file_info

    def _wait_for_active(self, file_name: str, max_wait_sec: int = 120):
        """Poll file state until ACTIVE."""
        get_url = f"{BASE_URL}/v1beta/{file_name}?key={self.api_key}"
        start_time = time.time()
        while time.time() - start_time < max_wait_sec:
            resp = requests.get(get_url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state")
                if state == "ACTIVE":
                    return True
                elif state == "FAILED":
                    raise RuntimeError(f"File processing failed on Gemini server: {data.get('error')}")
            time.sleep(2)
        raise TimeoutError("Timed out waiting for file to become ACTIVE on Gemini.")

    def get_available_models(self) -> List[str]:
        """
        Dynamically queries Google's ListModels API to find all active models
        that support generateContent for the user's API key.
        """
        if not self.api_key:
            return []

        models_found = []
        for ver in ["v1beta", "v1"]:
            try:
                url = f"{BASE_URL}/{ver}/models?key={self.api_key}"
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("models", []):
                        methods = item.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            name = item.get("name", "")
                            if name.startswith("models/"):
                                name = name[len("models/"):]
                            if name and name not in models_found:
                                models_found.append(name)
            except Exception as e:
                print(f"[GeminiService] Could not list models from {ver}: {e}")

        return models_found

    def find_viral_moments(
        self,
        file_uri: str,
        mime_type: str = "audio/mp3",
        min_duration: int = 15,
        max_duration: int = 60,
        num_clips: int = 4,
        topic_focus: str = "",
        model_name: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Asks Gemini to analyze the uploaded media and extract the best viral segments
        matching the duration range and criteria.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required.")

        system_instruction = (
            "You are a world-class viral video editor specializing in YouTube Shorts, "
            "TikTok, and Instagram Reels. Your superpower is detecting moments in long audio/video "
            "that capture viewer attention within 3 seconds, deliver high value/entertainment/emotion, "
            "and create viral retention loops."
        )

        prompt = f"""
Analyze the provided audio/video track thoroughly and extract the top {num_clips} most viral, engaging clips.

CRITICAL RULES:
1. Clip Duration: Every single clip's duration (end_time - start_time) MUST be between {min_duration} seconds and {max_duration} seconds.
2. Hook: Each clip MUST start with a compelling hook or strong statement within its first 3 seconds.
3. Natural Speech Boundaries: Do NOT cut mid-sentence or mid-word. Start cleanly when someone begins a thought or question, and end when the thought or punchline is resolved.
4. Timestamps: Provide accurate timestamps in seconds (float or int). e.g., start_time: 125.0, end_time: 178.5.
5. Virality Score: Rate each clip from 1 to 100 based on its emotional impact, curiosity factor, humor, debate, or practical insight.
6. Topic focus: {topic_focus if topic_focus else "Any standout moment (funny, insightful, shocking, controversial, or inspiring)."}

Output strictly a JSON object with this exact structure:
{{
  "clips": [
    {{
      "title": "Punchy Click-worthy Title (max 8 words)",
      "hook": "The opening hook statement that grabs attention",
      "why_viral": "Explanation of why this clip will perform well on social media",
      "virality_score": 95,
      "start_time": 120.0,
      "end_time": 165.0,
      "duration": 45.0,
      "transcript_excerpt": "Brief excerpt of what is said in this clip"
    }}
  ]
}}
"""

        # 1. Fetch available models dynamically from Google for this key
        discovered_models = self.get_available_models()
        print(f"[GeminiService] Discovered models for API key: {discovered_models}")

        # Sort discovered models: prioritize fast/flash models, then pro models
        flash_models = [m for m in discovered_models if "flash" in m.lower()]
        pro_models = [m for m in discovered_models if "pro" in m.lower() and m not in flash_models]
        other_models = [m for m in discovered_models if m not in flash_models and m not in pro_models]
        prioritized_models = flash_models + pro_models + other_models

        # If user explicitly passed a model_name, try that first
        models_to_try = []
        if model_name:
            models_to_try.append(model_name)

        models_to_try.extend(prioritized_models)

        # Fallback list if ListModels was empty
        fallbacks = [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash-001",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-001",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-pro"
        ]
        for fb in fallbacks:
            if fb not in models_to_try:
                models_to_try.append(fb)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "fileData": {
                                "mimeType": mime_type,
                                "fileUri": file_uri
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4
            }
        }

        last_error = None
        for m in models_to_try:
            for api_ver in ["v1beta", "v1"]:
                api_url = f"{BASE_URL}/{api_ver}/models/{m}:generateContent?key={self.api_key}"
                print(f"[GeminiService] Attempting generateContent with {api_ver}/models/{m}...")

                try:
                    resp = requests.post(api_url, json=payload, timeout=180)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                text_content = parts[0]["text"].strip()
                                # Clean potential markdown fences if present
                                if text_content.startswith("```json"):
                                    text_content = text_content[7:]
                                elif text_content.startswith("```"):
                                    text_content = text_content[3:]
                                if text_content.endswith("```"):
                                    text_content = text_content[:-3]
                                text_content = text_content.strip()

                                result = json.loads(text_content)
                                clips = result.get("clips", [])
                                clips.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
                                print(f"[GeminiService] Successfully retrieved {len(clips)} clips with {m} ({api_ver})")
                                return clips
                    else:
                        print(f"[GeminiService] {api_ver}/models/{m} returned {resp.status_code}")
                        last_error = f"Model {m} ({api_ver}) returned {resp.status_code}: {resp.text}"
                except Exception as e:
                    print(f"[GeminiService] Exception with {api_ver}/models/{m}: {e}")
                    last_error = f"Error with model {m}: {str(e)}"

        raise RuntimeError(f"Failed to generate viral clips with Gemini: {last_error}")

    def delete_file(self, file_name: str):
        """Cleans up the file from Gemini File API storage."""
        if not self.api_key or not file_name:
            return
        try:
            delete_url = f"{BASE_URL}/v1beta/{file_name}?key={self.api_key}"
            requests.delete(delete_url, timeout=10)
        except Exception:
            pass
