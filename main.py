from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from googleapiclient.discovery import build
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# YouTube API 配置
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

class SearchParams(BaseModel):
    query: str
    max_results: int = 10

class VideoData(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    channel_title: str
    published_at: str
    description: str

@app.get("/")
def read_root():
    return {"message": "YouTube Data API Service"}

@app.post("/search", response_model=List[VideoData])
async def search_videos(params: SearchParams):
    try:
        if not YOUTUBE_API_KEY:
            raise HTTPException(status_code=500, detail="YouTube API key not configured")

        request = youtube.search().list(
            q=params.query,
            part="snippet",
            maxResults=params.max_results,
            type="video"
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            video_data = VideoData(
                video_id=item["id"]["videoId"],
                title=item["snippet"]["title"],
                thumbnail_url=item["snippet"]["thumbnails"]["high"]["url"],
                channel_title=item["snippet"]["channelTitle"],
                published_at=item["snippet"]["publishedAt"],
                description=item["snippet"]["description"]
            )
            videos.append(video_data)

        return videos

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 