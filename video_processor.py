import os
import shutil
import subprocess
import yt_dlp
from typing import Optional, Dict, Any, Callable

def get_ffmpeg_path() -> str:
    """Finds ffmpeg executable from PATH, WinGet, imageio-ffmpeg, or local folder."""
    # 1. System PATH
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    # 2. Check WinGet package directory
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_dir = os.path.join(local_appdata, "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_dir):
            for root, _, files in os.walk(winget_dir):
                if "ffmpeg.exe" in files:
                    return os.path.join(root, "ffmpeg.exe")

    # 3. imageio-ffmpeg package
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except ImportError:
        pass

    # 4. Local bin folder or project root
    for candidate in [
        os.path.join(os.path.dirname(__file__), "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]:
        if os.path.exists(candidate):
            return candidate

    raise RuntimeError("FFmpeg not found! Please ensure FFmpeg is installed.")

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Retrieves basic video information (duration, width, height)."""
    ffmpeg = get_ffmpeg_path()
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # Check beside ffmpeg
        dir_name = os.path.dirname(ffmpeg)
        cand = os.path.join(dir_name, "ffprobe.exe" if os.name == "nt" else "ffprobe")
        if os.path.exists(cand):
            ffprobe = cand

    duration = 0.0
    width = 1920
    height = 1080

    if ffprobe and os.path.exists(ffprobe):
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height",
            "-of", "default=noprint_wrappers=1",
            video_path
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in res.stdout.strip().splitlines():
                if line.startswith("duration="):
                    duration = float(line.split("=")[1])
                elif line.startswith("width="):
                    width = int(line.split("=")[1])
                elif line.startswith("height="):
                    height = int(line.split("=")[1])
        except Exception:
            pass

    return {"duration": duration, "width": width, "height": height}

def extract_audio(video_path: str, output_audio_path: str) -> str:
    """
    Extracts audio from video to a lightweight, compressed 16kHz mono MP3
    so it uploads to Gemini in seconds.
    """
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i", video_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "48k",
        output_audio_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_audio_path

def cut_clip(
    video_path: str,
    start_time: float,
    duration: float,
    output_path: str,
    crop_mode: str = "blur",
    progress_callback: Optional[Callable[[str], None]] = None
) -> str:
    """
    Cuts a segment from video_path and converts it into 9:16 vertical format.
    
    crop_mode:
      - 'blur': 16:9 centered on a blurred 9:16 background (no faces cut off).
      - 'center': Hard 9:16 crop centered in video frame.
      - 'original': Keeps original aspect ratio.
    """
    ffmpeg = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if crop_mode == "blur":
        # Professional Reel/Shorts Blur background:
        # Scale to fill 1080x1920 and boxblur for background,
        # scale original keeping aspect ratio and overlay in center.
        filter_str = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=25:25[bg];"
            "[0:v]scale=1080:-1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
        cmd = [
            ffmpeg,
            "-y",
            "-ss", str(max(0.0, start_time)),
            "-i", video_path,
            "-t", str(duration),
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]
    elif crop_mode == "center":
        # Direct vertical crop centered:
        vf_filter = "crop=ih*(9/16):ih:(iw-ow)/2:0,scale=1080:1920"
        cmd = [
            ffmpeg,
            "-y",
            "-ss", str(max(0.0, start_time)),
            "-i", video_path,
            "-t", str(duration),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        # Original aspect ratio
        vf_filter = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        cmd = [
            ffmpeg,
            "-y",
            "-ss", str(max(0.0, start_time)),
            "-i", video_path,
            "-t", str(duration),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path
        ]

    if progress_callback:
        progress_callback(f"Rendering clip: {os.path.basename(output_path)}")

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {res.stderr.decode('utf-8', errors='ignore')}")

    # Generate thumbnail for web preview
    thumb_path = os.path.splitext(output_path)[0] + ".jpg"
    if crop_mode == "blur":
        thumb_cmd = [
            ffmpeg,
            "-y",
            "-ss", str(max(0.0, start_time + min(1.0, duration / 2))),
            "-i", video_path,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-vframes", "1",
            thumb_path
        ]
    else:
        thumb_cmd = [
            ffmpeg,
            "-y",
            "-ss", str(max(0.0, start_time + min(1.0, duration / 2))),
            "-i", video_path,
            "-vf", vf_filter,
            "-vframes", "1",
            thumb_path
        ]
    subprocess.run(thumb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return output_path

def download_youtube_video(url: str, output_dir: str) -> str:
    """Downloads a YouTube video using yt-dlp to output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    out_template = os.path.join(output_dir, "%(id)s_%(title).50s.%(ext)s")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': out_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # In case extension changed during merge
        base = os.path.splitext(filename)[0]
        for ext in [".mp4", ".mkv", ".webm"]:
            if os.path.exists(base + ext):
                return base + ext
        return filename
