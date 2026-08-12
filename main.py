from io import BytesIO
from json import JSONDecoder
from re import sub
from os.path import exists
from requests import get
from subprocess import STDOUT, call
from typing import TypedDict
from ytdownloader import fetchVideoInfo
from ytdownloader import downloadVideo
from time import sleep
from ytscraper import fetchVideoUrl


class TrackMetadata(TypedDict):
    avatarUrl: str
    index: str
    title: str
    artist: str
    album: str


def mp3FromVideo(mp3_file: str, mp4_file: str | None = None) -> None:
    """
    Creates an .mp3 file from input_fname. When output_fname is None,
    it will be named the same as input_fname.
    """
    mp4_file = mp3_file if mp4_file is None else mp4_file
    call(
        args=[
            "ffmpeg",
            "-y",
            "-i",
            mp4_file,
            mp3_file,
        ],
        stderr=STDOUT,
    )


def setTrackAlbumArt(album_art_file: str, meta: TrackMetadata) -> None:
    if exists(album_art_file):
        return

    albumArtUrl = str(meta["avatarUrl"])
    req = get(albumArtUrl)
    img = BytesIO(req.content)
    with open(album_art_file, "wb") as f:
        f.write(img.getbuffer())

    trackFile = f"track-{meta['index']}.mp3"
    cmd = "eyeD3"
    args = ["--add-image", f"{album_art_file}:FRONT_COVER", trackFile]
    call(
        [cmd, *args],
        stderr=STDOUT,
    )


def setTrackMetadata(audio_file: str, meta: TrackMetadata) -> None:
    cmd = "eyeD3"
    args = [
        "-a",
        meta["artist"],
        "-A",
        meta["album"],
        "-t",
        meta["title"],
        "-n",
        meta["index"],
        audio_file,
    ]

    call(
        [
            cmd,
            *args,
        ],
        stderr=STDOUT,
    )


def main():
    PATH_MUSIC = "media/tracks"
    PATH_ALBUM_ART = "media/album_art"
    PATH_VIDEO = "media/videos"
    META_FILENAME = "tracks.meta.json"
    # N = 1

    # load the track metadata
    with open(META_FILENAME, mode="r") as f:
        metaList: list[TrackMetadata] = JSONDecoder().decode(f.read())
        # metaList = metaList[:N]

    metaIndexes = list(map(lambda m: m["index"], metaList))
    metadata = dict(zip(metaIndexes, metaList))

    for id, meta in metadata.items():
        # skip iteration if audio file for this track is already present
        audioFilePath = f"{PATH_MUSIC}/track-{id}.mp3"
        if exists(audioFilePath):
            print(f"(track-{id}) skip: already downloaded audio file")
            continue

        # fetch the video url
        query = f"{meta['title']} by {meta['artist']}"
        result = fetchVideoUrl(query)
        if result["error"] is not None:
            print(f"(track-{id}) error: failed to fetch video url for '{query}'")
            print(f"(track-{id}) error:", result["error"])
            continue

        videoUrl = str(result["video_url"])

        # sanitize video title before saving to file system
        info = fetchVideoInfo(videoUrl)
        videoTitle = str(info.get("title", f"Video {id}"))

        videoTitle = sub(
            "[\\(\\)\\[\\]\"\\/?']+", "", videoTitle
        )  # pyright: ignore[reportCallIssue]

        videoTitle = sub("[\\s\\.]+", "_", videoTitle)
        videoFilePath = f"{PATH_VIDEO}/{videoTitle}.mp4"

        if not exists(videoFilePath):
            downloadVideo(videoUrl, output_fname=videoTitle, output_path=PATH_VIDEO)
        else:
            print(f"(track-{id}) already downloaded video file")

        mp3FromVideo(audioFilePath, videoFilePath)
        setTrackMetadata(audioFilePath, meta)

        albumArtFile = f"{PATH_ALBUM_ART}/album-track-{id}.jpg"
        setTrackAlbumArt(albumArtFile, meta)
        sleep(1.4)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
