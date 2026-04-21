from flask import Flask, render_template, request
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import pipeline
import re
import requests
import json

app = Flask(__name__)

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")


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


def format_time(seconds):
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def summarize(video_id):
    api = YouTubeTranscriptApi()

    try:
        transcript = api.fetch(video_id, languages=["en"])
    except Exception:
        try:
            transcript = api.fetch(video_id, languages=["hi"])
        except Exception:
            transcript = api.fetch(video_id)

    chunks = []
    current = ""
    start = 0

    for i, t in enumerate(transcript):
        if i == 0:
            start = t.start
        current += t.text + " "
        if len(current.split()) > 80:
            chunks.append((current.strip(), start))
            current = ""
            start = t.start

    if current:
        chunks.append((current.strip(), start))

    result = []
    for text, chunk_start in chunks[:6]:
        try:
            summary = summarizer(text, max_length=60, min_length=20, do_sample=False)[0]['summary_text']
            timestamp = format_time(chunk_start)
            link = f"https://www.youtube.com/watch?v={video_id}&t={int(chunk_start)}s"
            result.append({
                "time": timestamp,
                "text": summary,
                "link": link,
                "seconds": int(chunk_start)
            })
        except Exception:
            continue

    return result, chunks


def get_sentiment_from_transcript(chunks):
    pos_lines, neg_lines = [], []
    for text, _ in chunks[:10]:
        sentence = text[:512]
        try:
            result = sentiment_analyzer(sentence)[0]
            snippet = text[:100].strip() + "..."
            if result["label"] == "POSITIVE":
                pos_lines.append(snippet)
            else:
                neg_lines.append(snippet)
        except Exception:
            continue
    return pos_lines[:3], neg_lines[:3]


def get_real_rating(video_id):
    try:
        r = requests.get(
            f"https://returnyoutubedislikeapi.com/votes?videoId={video_id}",
            timeout=5
        )
        data = r.json()
        likes = data.get("likes", 1)
        dislikes = data.get("dislikes", 0)
        total = likes + dislikes
        pos = round((likes / total) * 100) if total > 0 else 80
        return pos, 100 - pos
    except Exception:
        return 80, 20


# def get_real_recommendations(video_id):
#     try:
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#         }
#         r = requests.get(
#             f"https://www.youtube.com/watch?v={video_id}",
#             headers=headers,
#             timeout=8
#         )
#         data = re.search(r'var ytInitialData = ({.*?});</script>', r.text)
#         if not data:
#             return []

#         yt = json.loads(data.group(1))
#         results = []

#         items = (
#             yt.get("contents", {})
#               .get("twoColumnWatchNextResults", {})
#               .get("secondaryResults", {})
#               .get("secondaryResults", {})
#               .get("results", [])
#         )

#         for item in items:
#             renderer = item.get("compactVideoRenderer")
#             if not renderer:
#                 continue
#             title = renderer.get("title", {}).get("simpleText", "")
#             vid_id = renderer.get("videoId", "")
#             views = renderer.get("viewCountText", {}).get("simpleText", "")
#             thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [{}])
#             thumb = thumbnails[-1].get("url", "") if thumbnails else ""

#             if title and vid_id:
#                 results.append({
#                     "title": title,
#                     "views": views,
#                     "link": f"https://www.youtube.com/watch?v={vid_id}",
#                     "thumb": thumb
#                 })

#             if len(results) == 3:
#                 break

#         return results
#     except Exception:
#         return []

def get_real_recommendations(video_id):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=headers,
            timeout=10
        )

        # Try multiple regex patterns YouTube uses
        patterns = [
            r'var ytInitialData = ({.*?});</script>',
            r'window\["ytInitialData"\] = ({.*?});',
            r'ytInitialData = ({.*?});'
        ]

        yt = None
        for pattern in patterns:
            match = re.search(pattern, r.text, re.DOTALL)
            if match:
                try:
                    yt = json.loads(match.group(1))
                    break
                except Exception:
                    continue

        if not yt:
            return get_recommendations_from_search(video_id)

        results = []

        # Try path 1: twoColumnWatchNextResults
        try:
            items = (
                yt.get("contents", {})
                  .get("twoColumnWatchNextResults", {})
                  .get("secondaryResults", {})
                  .get("secondaryResults", {})
                  .get("results", [])
            )
            for item in items:
                renderer = item.get("compactVideoRenderer")
                if not renderer:
                    continue
                title = renderer.get("title", {}).get("simpleText", "")
                vid_id = renderer.get("videoId", "")
                views = renderer.get("viewCountText", {}).get("simpleText", "")
                thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [{}])
                thumb = thumbnails[-1].get("url", "") if thumbnails else ""
                if title and vid_id:
                    results.append({
                        "title": title,
                        "views": views,
                        "link": f"https://www.youtube.com/watch?v={vid_id}",
                        "thumb": thumb
                    })
                if len(results) == 3:
                    break
        except Exception:
            pass

        # Try path 2: deeper nested structure YouTube sometimes uses
        if not results:
            try:
                secondary = (
                    yt.get("contents", {})
                      .get("twoColumnWatchNextResults", {})
                      .get("secondaryResults", {})
                )
                # sometimes it's one level deeper
                inner = secondary.get("secondaryResults", secondary)
                items = inner.get("results", [])
                for item in items:
                    for key in ["compactVideoRenderer", "compactAutoplayRenderer"]:
                        renderer = item.get(key)
                        if key == "compactAutoplayRenderer":
                            renderer = renderer.get("contents", [{}])[0].get("compactVideoRenderer") if renderer else None
                        if not renderer:
                            continue
                        title = renderer.get("title", {}).get("simpleText", "")
                        vid_id = renderer.get("videoId", "")
                        views = renderer.get("viewCountText", {}).get("simpleText", "")
                        thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [{}])
                        thumb = thumbnails[-1].get("url", "") if thumbnails else ""
                        if title and vid_id:
                            results.append({
                                "title": title,
                                "views": views,
                                "link": f"https://www.youtube.com/watch?v={vid_id}",
                                "thumb": thumb
                            })
                        if len(results) == 3:
                            break
                    if len(results) == 3:
                        break
            except Exception:
                pass

        if not results:
            return get_recommendations_from_search(video_id)

        return results

    except Exception:
        return get_recommendations_from_search(video_id)


def get_recommendations_from_search(video_id):
    """Fallback: search YouTube for related videos using video title"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # First get the video title
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers=headers, timeout=8
        )
        title_match = re.search(r'<title>(.*?) - YouTube</title>', r.text)
        query = title_match.group(1).strip() if title_match else "popular videos"

        # Search YouTube for related videos
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        r2 = requests.get(search_url, headers=headers, timeout=8)

        patterns = [
            r'var ytInitialData = ({.*?});</script>',
            r'ytInitialData = ({.*?});'
        ]
        yt = None
        for pattern in patterns:
            match = re.search(pattern, r2.text, re.DOTALL)
            if match:
                try:
                    yt = json.loads(match.group(1))
                    break
                except Exception:
                    continue

        if not yt:
            return []

        results = []
        contents = (
            yt.get("contents", {})
              .get("twoColumnSearchResultsRenderer", {})
              .get("primaryContents", {})
              .get("sectionListRenderer", {})
              .get("contents", [])
        )

        for section in contents:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                renderer = item.get("videoRenderer")
                if not renderer:
                    continue
                title_runs = renderer.get("title", {}).get("runs", [])
                title = title_runs[0].get("text", "") if title_runs else ""
                vid_id = renderer.get("videoId", "")
                if vid_id == video_id:
                    continue  # skip the same video
                views = renderer.get("viewCountText", {}).get("simpleText", "")
                thumbnails = renderer.get("thumbnail", {}).get("thumbnails", [{}])
                thumb = thumbnails[-1].get("url", "") if thumbnails else ""
                if title and vid_id:
                    results.append({
                        "title": title,
                        "views": views,
                        "link": f"https://www.youtube.com/watch?v={vid_id}",
                        "thumb": thumb
                    })
                if len(results) == 3:
                    break
            if len(results) == 3:
                break

        return results

    except Exception:
        return []


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        video_id = get_video_id(url)

        if not video_id:
            return render_template("index.html", error="Invalid YouTube URL. Please try again.")

        try:
            summary, chunks = summarize(video_id)
            pos, neg = get_real_rating(video_id)
            pos_comments, neg_comments = get_sentiment_from_transcript(chunks)
            recs = get_real_recommendations(video_id)

            return render_template(
                "index.html",
                summary=summary,
                video_url=url,
                video_id=video_id,
                pos=pos,
                neg=neg,
                pos_comments=pos_comments,
                neg_comments=neg_comments,
                recs=recs
            )
        except Exception as e:
            return render_template("index.html", error=f"Could not process video: {str(e)}")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)