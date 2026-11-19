# ⚡ ClipPulse AI - Viral Video Shorts & Reels Clipper

An AI-powered video clipping tool that turns long videos (e.g. 1-2 hour podcasts, interviews, or gameplay) into high-retention, viral 9:16 vertical shorts for TikTok, Instagram Reels, and YouTube Shorts.

---

## 🌟 Key Features

1. **Smart Viral Moment Detection (Google Gemini AI):**
   - Automatically extracts lightweight audio and sends it to Google Gemini Multimodal API.
   - Detects the most engaging hooks, punchlines, and high-retention moments.
   - Generates catchy titles, viral explanations, and virality scores (1-100).
   - Natural speech boundaries: cuts cleanly without clipping sentences abruptly mid-word.

2. **Customizable Clip Duration (10s to 120s / 2 Minutes):**
   - Interactive sliders to choose both **Minimum Duration** (10s - 60s) and **Maximum Duration** (30s - 120s).
   - Choose the number of clips you want (1 to 8 clips).

3. **Vertical 9:16 Cropping Engine:**
   - **Blur 9:16 (Recommended for Podcasts):** Fits the original 16:9 widescreen in the center with a stylized blurred background so no faces or heads are cut off.
   - **Center 9:16:** Direct full-screen vertical crop.
   - **16:9 Original:** Keeps widescreen aspect ratio.

4. **Input Flexibility:**
   - **Upload Local MP4 Video (Priority):** Smooth drag-and-drop file upload with live progress bar.
   - **YouTube Link Support:** Direct download and clipping via `yt-dlp`.

5. **Built-in Web Interface:**
   - Modern, responsive dark-mode UI with live video preview, real-time generation progress, and a 9:16 clips gallery with instant MP4 download buttons.

---

## 🚀 How to Run

### Method 1: One-Click Run (Windows)
Simply double-click `run.bat` in this folder. It will launch the application and open your browser at `http://localhost:5000`.

### Method 2: Manual Terminal Run
```bash
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Start the application
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 🔑 Gemini API Key Setup
You can get a 100% free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
You can either:
- Enter your key directly in the Web UI modal (it gets remembered safely in your browser).
- Or paste it into `.env`:
  ```env
  GEMINI_API_KEY=AIzaSy...
  ```
