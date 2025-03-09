from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import json

# 创建 FastAPI 应用
app = FastAPI(title="YouTube 视频 API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./youtube_videos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 数据库模型
class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(50), unique=True, index=True)
    title = Column(String(500))
    channel = Column(String(200))
    upload_date = Column(String(50))
    view_count = Column(Integer, default=0)
    duration = Column(String(50))
    thumbnail = Column(String(500))
    like_count = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# Pydantic 模型
class VideoBase(BaseModel):
    video_id: str
    title: str
    channel: str
    upload_date: str
    view_count: int = 0
    duration: str
    thumbnail: str
    like_count: int = 0
    description: Optional[str] = None

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# 辅助函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API 路由
@app.post("/videos/", response_model=Video)
async def create_video(video: VideoCreate):
    db = SessionLocal()
    try:
        # 检查视频是否已存在
        existing_video = db.query(VideoModel).filter(VideoModel.video_id == video.video_id).first()
        if existing_video:
            return existing_video
            
        db_video = VideoModel(**video.dict())
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        return db_video
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@app.post("/videos/batch/", response_model=List[Video])
async def create_videos_batch(videos: List[VideoCreate]):
    db = SessionLocal()
    try:
        db_videos = []
        for video in videos:
            # 检查视频是否已存在
            existing_video = db.query(VideoModel).filter(VideoModel.video_id == video.video_id).first()
            if existing_video:
                db_videos.append(existing_video)
                continue
                
            db_video = VideoModel(**video.dict())
            db.add(db_video)
            db_videos.append(db_video)
        
        db.commit()
        return db_videos
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@app.get("/videos/", response_model=List[Video])
async def get_videos(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    try:
        videos = db.query(VideoModel).offset(skip).limit(limit).all()
        return videos
    finally:
        db.close()

@app.get("/videos/{video_id}", response_model=Video)
async def get_video(video_id: str):
    db = SessionLocal()
    try:
        video = db.query(VideoModel).filter(VideoModel.video_id == video_id).first()
        if video is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
    finally:
        db.close()

@app.get("/videos/search/{query}", response_model=List[Video])
async def search_videos(query: str):
    db = SessionLocal()
    try:
        videos = db.query(VideoModel).filter(
            VideoModel.title.ilike(f"%{query}%")
        ).all()
        return videos
    finally:
        db.close()

# 根路由
@app.get("/")
async def root():
    return {"message": "YouTube 视频 API 服务正在运行"} 