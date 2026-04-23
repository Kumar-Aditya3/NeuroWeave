from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


Topic = Literal[
    "tech",
    "education",
    "anime",
    "fitness",
    "philosophy",
    "self-help",
    "news",
    "unknown",
]
Sentiment = Literal["positive", "neutral", "negative"]
Vibe = Literal["calm", "balanced", "intense", "dark"]
FeedbackAction = Literal["keep", "skip", "like"]
ActivitySource = Literal["browser_tab", "active_window", "game", "ocr_text", "manual"]


class PageIngestRequest(BaseModel):
    user_id: str = Field(default="kumar")
    device_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    source: Literal["extension"] = Field(default="extension")
    url: HttpUrl
    title: str
    selected_text: Optional[str] = None
    timestamp: Optional[datetime] = None


class PdfIngestRequest(BaseModel):
    user_id: str = Field(default="kumar")
    device_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    source: Literal["pdf_upload"] = Field(default="pdf_upload")
    filename: str
    text: str = Field(min_length=1)
    timestamp: Optional[datetime] = None


class IngestResponse(BaseModel):
    event_id: int
    deduped: bool = False
    topic_scores: Dict[str, float]
    sentiment: Sentiment
    vibe: Vibe
    classifier_mode: str = "keyword_fallback"


class ActivityIngestRequest(BaseModel):
    user_id: str = Field(default="kumar")
    device_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    source: ActivitySource
    event_type: ActivitySource
    title: str = Field(min_length=1)
    url: Optional[HttpUrl] = None
    selected_text: Optional[str] = None
    content_text: Optional[str] = None
    process_name: Optional[str] = None
    category: Optional[str] = None
    timestamp: Optional[datetime] = None


class ContextRecommendation(BaseModel):
    user_id: str
    primary_topic: Topic
    topic_scores: Dict[str, float]
    wallpaper_tags: list[str]
    wallpaper_query: str
    wallpaper_preview_url: str
    wallpaper_palette: list[str]
    wallpaper_source: str
    wallpaper_cached_path: Optional[str] = None
    wallpaper_alternates: list[dict] = Field(default_factory=list)
    music_mood: str
    quote_style: str
    vibe: Vibe
    classifier_mode: str = "embedding_primary"
    explanation: str = ""


class FeedbackRequest(BaseModel):
    user_id: str = Field(default="kumar")
    recommendation_topic: Topic
    action: FeedbackAction


class HealthResponse(BaseModel):
    status: str


class SourceDevice(BaseModel):
    device_id: str
    client_name: str
    last_seen_at: str


class SourcesResponse(BaseModel):
    user_id: str
    sources: list[SourceDevice]


class RecentEvent(BaseModel):
    id: int
    user_id: str
    device_id: Optional[str]
    client_name: Optional[str]
    source: str
    event_type: str
    url: Optional[str]
    title: Optional[str]
    sentiment: Sentiment
    vibe: Vibe
    created_at: str
    classifier_mode: Optional[str] = None


class RecentEventsResponse(BaseModel):
    user_id: str
    events: list[RecentEvent]


class DashboardResponse(BaseModel):
    user_id: str
    recommendation: ContextRecommendation
    events: list[RecentEvent]
    sources: list[SourceDevice]
