#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "youtube-transcript-api",
# ]
# ///
"""
fetch_transcript.py - YouTube動画のトランスクリプトをMarkdown形式で出力

Usage: uv run fetch_transcript.py <URL>

出力: stdout にMarkdown形式のコンテキスト（タイトル・チャンネル・トランスクリプト）
"""

import json
import re
import sys
import urllib.error
import urllib.request


def extract_video_id(url: str) -> str | None:
    patterns = [
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def get_metadata(url: str) -> dict:
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    with urllib.request.urlopen(oembed_url, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return {
        "title": data.get("title", "Unknown"),
        "channel": data.get("author_name", "Unknown"),
    }


def get_transcript(video_id: str) -> tuple[str, str]:
    from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.list(video_id)

    try:
        transcript = transcript_list.find_transcript(["en", "ja"])
    except NoTranscriptFound:
        transcript = next(iter(transcript_list), None)
        if transcript is None:
            raise NoTranscriptFound(video_id, [])

    fetched = transcript.fetch()
    lang_code = fetched.language_code
    text = " ".join(snippet.text for snippet in fetched)
    return text, lang_code


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run fetch_transcript.py <YouTube URL>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]

    video_id = extract_video_id(url)
    if not video_id:
        print(f"ERROR: Could not extract video ID from URL: {url}", file=sys.stderr)
        sys.exit(1)

    try:
        metadata = get_metadata(url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"ERROR: Failed to fetch video metadata: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        transcript_text, lang_code = get_transcript(video_id)
    except Exception as e:
        print(f"ERROR: Failed to fetch transcript: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"# {metadata['title']}")
    print()
    print(f"- **Channel**: {metadata['channel']}")
    print(f"- **URL**: {url}")
    print()
    print(f"## Transcript ({lang_code})")
    print()
    print(transcript_text)


if __name__ == "__main__":
    main()
