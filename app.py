import os
import sys
import uuid
import json
import threading
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

import video_processor
from gemini_service import GeminiService

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB max upload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# In-memory jobs tracking
jobs = {}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'mov', 'mkv', 'avi', 'webm'}

@app.route("/")
def index():
    has_env_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return render_template("index.html", has_env_key=has_env_key)

@app.route("/api/config", methods=["GET"])
def get_config():
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    return jsonify({
        "has_env_key": bool(env_key),
        "default_min_duration": 15,
        "default_max_duration": 60,
    })

@app.route("/api/upload", methods=["POST"])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid video format. Supported: MP4, MKV, MOV, WEBM"}), 400

    video_id = str(uuid.uuid4())[:8]
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{video_id}_{secure_filename(file.filename)}"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    # Basic info
    try:
        info = video_processor.get_video_info(save_path)
    except Exception:
        info = {"duration": 0, "width": 1920, "height": 1080}

    return jsonify({
        "success": True,
        "video_id": video_id,
        "filename": filename,
        "duration": info.get("duration", 0),
        "width": info.get("width", 1920),
        "height": info.get("height", 1080),
        "preview_url": f"/uploads/{filename}"
    })

@app.route("/api/youtube", methods=["POST"])
def download_yt():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "YouTube URL is required"}), 400

    try:
        file_path = video_processor.download_youtube_video(url, UPLOAD_FOLDER)
        filename = os.path.basename(file_path)
        video_id = str(uuid.uuid4())[:8]
        info = video_processor.get_video_info(file_path)
        return jsonify({
            "success": True,
            "video_id": video_id,
            "filename": filename,
            "duration": info.get("duration", 0),
            "width": info.get("width", 1920),
            "height": info.get("height", 1080),
            "preview_url": f"/uploads/{filename}"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to download YouTube video: {str(e)}"}), 500

@app.route("/api/process", methods=["POST"])
def start_processing():
    data = request.get_json() or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    video_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "Uploaded video file not found on server"}), 404

    api_key = data.get("api_key", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Gemini API Key is required. Please enter your API key."}), 400

    min_duration = int(data.get("min_duration", 15))
    max_duration = int(data.get("max_duration", 60))
    num_clips = int(data.get("num_clips", 4))
    crop_mode = data.get("crop_mode", "blur")
    topic_focus = data.get("topic_focus", "").strip()

    job_id = str(uuid.uuid4())[:10]
    jobs[job_id] = {
        "status": "queued",
        "progress": 5,
        "message": "Initializing video clipping process...",
        "clips": [],
        "error": None,
        "created_at": time.time()
    }

    # Run processing thread
    thread = threading.Thread(
        target=_process_video_thread,
        args=(job_id, video_path, api_key, min_duration, max_duration, num_clips, crop_mode, topic_focus)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "job_id": job_id})

def _process_video_thread(job_id, video_path, api_key, min_duration, max_duration, num_clips, crop_mode, topic_focus):
    try:
        # Step 1: Extract lightweight audio
        jobs[job_id]["status"] = "extracting_audio"
        jobs[job_id]["progress"] = 15
        jobs[job_id]["message"] = "Extracting audio stream for AI analysis..."
        
        audio_name = f"audio_{job_id}.mp3"
        audio_path = os.path.join(UPLOAD_FOLDER, audio_name)
        video_processor.extract_audio(video_path, audio_path)

        # Step 2: Upload audio to Gemini
        jobs[job_id]["status"] = "uploading_ai"
        jobs[job_id]["progress"] = 35
        jobs[job_id]["message"] = "Uploading audio to Google Gemini AI..."
        
        gemini = GeminiService(api_key=api_key)
        file_info = gemini.upload_file(audio_path, mime_type="audio/mp3")
        file_uri = file_info.get("uri")
        file_name = file_info.get("name")

        # Step 3: Analyze audio with Gemini to find viral moments
        jobs[job_id]["status"] = "analyzing"
        jobs[job_id]["progress"] = 55
        jobs[job_id]["message"] = f"AI is finding top {num_clips} viral moments ({min_duration}s - {max_duration}s)..."

        moments = gemini.find_viral_moments(
            file_uri=file_uri,
            mime_type="audio/mp3",
            min_duration=min_duration,
            max_duration=max_duration,
            num_clips=num_clips,
            topic_focus=topic_focus
        )

        # Clean up Gemini file
        gemini.delete_file(file_name)
        if os.path.exists(audio_path):
            os.remove(audio_path)

        if not moments:
            raise RuntimeError("Gemini could not identify any viral moments matching the criteria.")

        # Step 4: Render the 9:16 clips
        jobs[job_id]["status"] = "rendering"
        jobs[job_id]["progress"] = 70
        jobs[job_id]["message"] = f"Rendering {len(moments)} viral 9:16 clips with FFmpeg..."

        rendered_clips = []
        total_clips = len(moments)

        for idx, moment in enumerate(moments, start=1):
            start = float(moment.get("start_time", 0.0))
            end = float(moment.get("end_time", start + 30.0))
            clip_dur = max(5.0, end - start)

            clip_filename = f"clip_{job_id}_{idx}.mp4"
            out_clip_path = os.path.join(OUTPUT_FOLDER, clip_filename)

            progress_val = 70 + int((idx / total_clips) * 25)
            jobs[job_id]["progress"] = progress_val
            jobs[job_id]["message"] = f"Rendering clip {idx}/{total_clips}: '{moment.get('title', 'Clip')}'..."

            video_processor.cut_clip(
                video_path=video_path,
                start_time=start,
                duration=clip_dur,
                output_path=out_clip_path,
                crop_mode=crop_mode
            )

            thumb_filename = f"clip_{job_id}_{idx}.jpg"
            rendered_clips.append({
                "clip_id": f"{job_id}_{idx}",
                "title": moment.get("title", f"Viral Moment #{idx}"),
                "hook": moment.get("hook", ""),
                "why_viral": moment.get("why_viral", ""),
                "virality_score": moment.get("virality_score", 85),
                "start_time": start,
                "end_time": end,
                "duration": round(clip_dur, 1),
                "transcript_excerpt": moment.get("transcript_excerpt", ""),
                "video_url": f"/outputs/{clip_filename}",
                "thumbnail_url": f"/outputs/{thumb_filename}",
                "filename": clip_filename
            })

        # Done!
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = f"Successfully generated {len(rendered_clips)} viral clips!"
        jobs[job_id]["clips"] = rendered_clips

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Error: {str(e)}"

@app.route("/api/status/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Viral Video Clipper on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
