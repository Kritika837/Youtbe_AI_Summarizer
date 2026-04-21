import re
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline


# 🔹 Extract video ID
def get_video_id(url):
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# 🔹 Load model
def load_model():
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")


# 🔹 Convert seconds → mm:ss
def format_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# 🔹 Main summarization
def summarize_video(url, summarizer):
    video_id = get_video_id(url)
    if not video_id:
        return "Invalid YouTube URL"

    api = YouTubeTranscriptApi()

    # 🔹 Language fallback
    try:
        transcript = api.fetch(video_id, languages=["en"])
    except:
        try:
            transcript = api.fetch(video_id, languages=["hi"])
        except:
            transcript = api.fetch(video_id)

    # 🔥 Create chunks WITH timestamps
    chunks = []
    current_text = ""
    start_time = 0

    for i, t in enumerate(transcript):
        if i == 0:
            start_time = t.start

        current_text += t.text + " "

        if len(current_text.split()) > 80:
            chunks.append((current_text.strip(), start_time))
            current_text = ""
            start_time = t.start

    if current_text:
        chunks.append((current_text.strip(), start_time))

    # 🔥 Limit chunks (for speed)
    chunks = chunks[:5]

    results = []

    for text, start in chunks:
        try:
            summary = summarizer(
                text,
                max_length=60,
                min_length=20,
                do_sample=False
            )[0]['summary_text']

            timestamp = format_time(start)
            youtube_link = f"https://www.youtube.com/watch?v={video_id}&t={int(start)}s"

            # 🔥 Clickable + clean format
            results.append(f"[▶ {timestamp}]({youtube_link})  \n• {summary}")

        except:
            continue

    if not results:
        return "Could not generate summary"

    return "\n\n".join(results)