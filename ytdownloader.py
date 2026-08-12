import os
import subprocess
import sys
from datetime import datetime

import yt_dlp


def checkFFmpeg():
    """
    Check if FFmpeg is installed and accessible.
    Returns True if FFmpeg is available, False otherwise.
    """
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def formatSize(bytes):
    """
    Convert bytes to human readable format, making file sizes easier to understand.
    Scales from bytes up to gigabytes automatically.
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} GB"


def progressHook(d):
    """
    Display download progress with detailed information about speed and time remaining.
    Provides real-time feedback during the download process.
    """
    if d["status"] == "downloading":
        downloaded = d.get("downloaded_bytes", 0)
        total = d.get("total_bytes", 0) or d.get("total_bytes_estimate", 0)

        if total:
            percentage = (downloaded / total) * 100
            speed = d.get("speed", 0)
            speed_str = formatSize(speed) + "/s" if speed else "N/A"

            eta = d.get("eta", None)
            eta_str = (
                str(datetime.fromtimestamp(eta).strftime("%M:%S")) if eta else "N/A"
            )

            progress = (
                f"\nprogress: {percentage:.1f}% | speed: {speed_str} | eta: {eta_str}"
            )
            sys.stdout.write(progress)
            sys.stdout.flush()


def getBestFormat(target_height, ffmpeg_available):
    """
    Select the best video format based on desired quality and FFmpeg availability.
    Handles both cases where FFmpeg is available and where it isn't.
    """
    if ffmpeg_available:
        # when ffmpeg is available, we can use separate video and audio streams
        return f"bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={target_height}][ext=mp4]/best"
    else:
        # when ffmpeg isn't available, we need a merged format
        return f"best[height<={target_height}][ext=mp4]/best[ext=mp4]/best"


def fetchVideoInfo(url: str, opts: yt_dlp._Params | None = None):
    defaultOpts = {"verbose": False}
    opts = defaultOpts if opts is None else opts  # type: ignore

    print(f"fetching video information for '{url}'..")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            info = {}

    print("done.")
    return info


def downloadVideo(
    url,
    preferred_quality=None,
    ydl_opts=None,
    output_fname=None,
    output_path="downloads",
):
    """
    Download a YouTube video with specified quality using yt-dlp.
    Handles cases both with and without FFmpeg installed.

    Args:
        url (str): YouTube video URL
        preferred_quality (str): Preferred video quality (e.g., '720p', '1080p')
        output_path (str): Directory to save the downloaded video

    Returns (dict):
        The video info object.
    """
    default_opts: yt_dlp._Params = {
        "progress_hooks": [progressHook],
        "outtmpl": os.path.join(
            output_path,
            "%(title)s.%(ext)s" if output_fname is None else f"{output_fname}.%(ext)s",
        ),
        "verbose": False,
        "js_runtimes": {
            "node": {"path": "/home/leo/.nvm/versions/node/v20.20.2/bin/node"}
        },
    }
    ydl_opts = default_opts if ydl_opts is None else ydl_opts

    try:
        ffmpeg_available = checkFFmpeg()
        if not ffmpeg_available:
            print("\nffmpeg is not installed. some options may be limited.")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        info = fetchVideoInfo(url)

        print(f"\n  video title: {info.get('title', '<Unknown>')}")
        duration = info.get("duration", 0)
        duration = 0 if not isinstance(duration, int) else duration
        print(f"  duration: {duration // 60}:{duration % 60:02d}")

        formats = info.get("formats", [])
        formats = [] if not isinstance(formats, list) else formats
        quality_set = set()

        for f in formats:
            height = f.get("height")
            # if ffmpeg isn't available, only include formats that have both video and audio
            if height and (ffmpeg_available or f.get("acodec") != "none"):
                quality_set.add(f"{height}p")

        quality_list = sorted(quality_set, key=lambda x: int(x.replace("p", "")))
        preferred_quality = quality_list[len(quality_list) // 2]

        # set format based on selected quality and ffmpeg availability
        height = int(preferred_quality.replace("p", ""))
        ydl_opts["format"] = getBestFormat(height, ffmpeg_available)

        print(f"\n  downloading video in {preferred_quality}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ydl.build_request_director
            ydl.download([url])
            print("\n  done.")
        return info

    except Exception as e:
        print(f"download error: {str(e)}")
        return {}
