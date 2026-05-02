export type Topic =
  | "tech"
  | "education"
  | "anime"
  | "fitness"
  | "philosophy"
  | "self-help"
  | "news"
  | "unknown";

export type Vibe = "calm" | "balanced" | "intense" | "dark";
export type ConsoleDensity = "comfortable" | "compact";
export type ThemeMode = "dark" | "light";
export type RecommendationIntensity = "calm" | "balanced" | "strong";
export type ClassifierMode = "embedding_primary" | "keyword_fallback";
export type WallpaperStyle = "minimal" | "cinematic" | "warm" | "neon" | "editorial";
export type WallpaperProvider = "curated_unsplash" | "generated_future";

export type Settings = {
  backendUrl: string;
  apiKey: string;
  userId: string;
  refreshIntervalSeconds: number;
  enableDiffusionGeneration: boolean;
  autoApplyWallpaper: boolean;
  wallpaperChangeCooldownMinutes: number;
  themeMode: ThemeMode;
  consoleDensity: ConsoleDensity;
  recommendationIntensity: RecommendationIntensity;
  classifierMode: ClassifierMode;
  wallpaperStyle: WallpaperStyle;
  wallpaperProvider: WallpaperProvider;
  topicWeights: Record<Topic, number>;
  privacy: {
    showBrowser: boolean;
    showApps: boolean;
    showOcr: boolean;
  };
};

export type Recommendation = {
  user_id: string;
  primary_topic: Topic;
  topic_scores: Record<Topic, number>;
  wallpaper_tags: string[];
  wallpaper_query: string;
  wallpaper_preview_url: string;
  wallpaper_palette: string[];
  wallpaper_source: string;
  wallpaper_provider: WallpaperProvider;
  wallpaper_rationale: string;
  wallpaper_cached_path?: string | null;
  wallpaper_alternates: Array<{
    preview_url: string;
    cached_path?: string | null;
    source: string;
  }>;
  music_mood: string;
  quote_style: string;
  vibe: Vibe;
  classifier_mode: ClassifierMode;
  explanation: string;
  // Data visibility fields (detailed explainability)
  prompt_components?: {
    arc_name?: string;
    vibe_base?: string;
    topic_base?: string;
    style_hint?: string;
    novelty_hint?: string;
  };
  generation_metadata?: {
    model?: string;
    device?: string;
    steps?: number;
    guidance_scale?: number;
    seed?: string;
    width?: number;
    height?: number;
    fallback_used?: boolean;
    fallback_reason?: string;
    fallback_to?: string;
  };
  novelty_context?: {
    recent_count?: number;
    novelty_hint_applied?: boolean;
    similarity_score?: number;
  };
  classification_confidence?: {
    topic_scores_all?: Record<Topic, number>;
    primary_topic_confidence?: number;
    classifier_mode?: ClassifierMode;
    topic_weight_bias?: Record<Topic, number> | null;
    normalized_intensity?: "low" | "balanced" | "high";
    preference_profile?: Record<string, Record<string, number>> | null;
  };
  session_context?: {
    signature: string;
    kind: string;
    stability: number;
    shift_score: number;
    event_streak: number;
    minutes_covered: number;
    dominant_category: string;
    dominant_process: string;
  };
};

export type RecentEvent = {
  id: number;
  user_id: string;
  device_id: string | null;
  client_name: string | null;
  source: string;
  event_type: string;
  url: string | null;
  title: string | null;
  category?: string | null;
  duration_seconds?: number | null;
  sentiment: "positive" | "neutral" | "negative";
  vibe: Vibe;
  created_at: string;
  classifier_mode?: ClassifierMode | string | null;
};

export type CurrentArc = {
  name: string;
  strength: number;
  dominant_topic: Topic;
  vibe: Vibe;
  keywords: string[];
  sample_titles: string[];
};

export type SourceMix = {
  browser: number;
  app: number;
  game: number;
  ocr: number;
  mobile: number;
};

export type SourcesResponse = {
  user_id: string;
  sources: Array<{
    device_id: string;
    client_name: string;
    last_seen_at: string;
  }>;
};

export type DashboardData = {
  online: boolean;
  lastSync: string | null;
  recommendation: Recommendation | null;
  events: RecentEvent[];
  sources: SourcesResponse["sources"];
  currentArcs: CurrentArc[];
  sourceMix: SourceMix;
  error?: string;
};

export type DashboardResponse = {
  user_id: string;
  recommendation: Recommendation;
  events: RecentEvent[];
  sources: SourcesResponse["sources"];
  current_arcs: CurrentArc[];
  source_mix: SourceMix;
};

export type WallpaperSetResponse = {
  ok: boolean;
  message: string;
  path?: string;
  code?: string;
  primaryError?: string;
};

declare global {
  interface Window {
    neuroWeaveSettings: {
      get: () => Promise<Settings>;
      set: (settings: Partial<Settings>) => Promise<Settings>;
    };
    neuroWeaveDesktop: {
      setWallpaper: (payload: { previewUrl?: string; cachedPath?: string | null }) => Promise<WallpaperSetResponse>;
    };
  }
}
