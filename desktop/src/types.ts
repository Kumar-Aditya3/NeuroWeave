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

export type Settings = {
  backendUrl: string;
  apiKey: string;
  userId: string;
  refreshIntervalSeconds: number;
  themeMode: ThemeMode;
  consoleDensity: ConsoleDensity;
  recommendationIntensity: RecommendationIntensity;
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
  music_mood: string;
  quote_style: string;
  vibe: Vibe;
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
  sentiment: "positive" | "neutral" | "negative";
  vibe: Vibe;
  created_at: string;
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
  error?: string;
};

declare global {
  interface Window {
    neuroWeaveSettings: {
      get: () => Promise<Settings>;
      set: (settings: Partial<Settings>) => Promise<Settings>;
    };
  }
}
