from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


Topic = Literal["tech", "anime", "fitness", "philosophy", "self-help", "news"]
Sentiment = Literal["positive", "neutral", "negative"]
Vibe = Literal["calm", "balanced", "intense", "dark"]
FeedbackAction = Literal["keep", "skip", "like"]


class PageIngestRequest(BaseModel):
    user_id: str = Field(default="default")
    source: Literal["extension"] = Field(default="extension")
    url: HttpUrl
    title: str
    selected_text: Optional[str] = None
    timestamp: Optional[datetime] = None


class PdfIngestRequest(BaseModel):
    user_id: str = Field(default="default")
    source: Literal["pdf_upload"] = Field(default="pdf_upload")
    filename: str
    text: str = Field(min_length=1)
    timestamp: Optional[datetime] = None


class IngestResponse(BaseModel):
    event_id: int
    topic_scores: Dict[str, float]
    sentiment: Sentiment
    vibe: Vibe


class ContextRecommendation(BaseModel):
    user_id: str
    primary_topic: Topic
    topic_scores: Dict[str, float]
    wallpaper_tags: list[str]
    music_mood: str
    quote_style: str
    vibe: Vibe


class FeedbackRequest(BaseModel):
    user_id: str = Field(default="default")
    recommendation_topic: Topic
    action: FeedbackAction


class HealthResponse(BaseModel):
    status: str
