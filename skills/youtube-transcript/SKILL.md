---
name: youtube-transcript
description: Fetch subtitles/transcripts from YouTube videos and use them as context for summarization, analysis, translation, or Q&A. Use this skill whenever a user shares a YouTube URL and asks to summarize, explain, or discuss the video content, or when they explicitly ask for subtitles or a transcript. Trigger on any youtube.com, youtu.be, or YouTube Shorts link that appears in conversation where understanding the video content is needed.
allowed-tools: Bash(uv run */fetch_transcript.py *)
---

# YouTube Transcript Fetcher

Fetches subtitle text from a YouTube video and outputs it as Markdown. The retrieved transcript can then be used for downstream tasks such as summarization, analysis, translation, or answering questions about the video.

## Prerequisites

- `uv` must be installed on the system (used for dependency resolution and script execution)
- Network access to YouTube

## Usage

```bash
uv run <skill-dir>/scripts/fetch_transcript.py "<YouTube URL>"
```

Output goes to stdout in Markdown format. Pipe or redirect as needed:

```bash
# Capture to a variable
TRANSCRIPT=$(uv run <skill-dir>/scripts/fetch_transcript.py "https://www.youtube.com/watch?v=XXXXXXXXXXX")

# Save to a file
uv run <skill-dir>/scripts/fetch_transcript.py "https://youtu.be/XXXXXXXXXXX" > transcript.md
```

### Supported URL formats

The script auto-extracts the video ID from any of these:

- `https://www.youtube.com/watch?v=XXXXXXXXXXX`
- `https://youtu.be/XXXXXXXXXXX`
- `https://www.youtube.com/shorts/XXXXXXXXXXX`

### Output format

```markdown
# Video Title

- **Channel**: Channel Name
- **URL**: Original URL

## Transcript (language_code)

Full subtitle text joined with spaces as plain text.
```

## Language priority

Transcript lookup follows this order:

1. English (en) or Japanese (ja) manual captions
2. If neither is found, the first available transcript track

Auto-generated captions are included. Videos with no captions at all will error.

## Error cases

The script prints to stderr and exits non-zero on failure. Common causes:

- **Cannot extract video ID** — unsupported or malformed URL
- **Metadata fetch failed** — video is private, deleted, or network error
- **Transcript fetch failed** — captions are disabled or none exist

When an error occurs, inform the user and suggest they check the video's visibility and caption settings.

## Typical workflow

When a user shares a YouTube link and asks about its content:

1. Run the script to fetch the transcript
2. Read the output to understand the video content
3. Perform the requested task (summarize, analyze, answer questions, etc.)
