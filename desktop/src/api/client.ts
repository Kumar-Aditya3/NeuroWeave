import type { DashboardResponse, RecentEvent, Recommendation, Settings, SourcesResponse, Topic } from "../types";

async function request<T>(settings: Settings, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${settings.backendUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": settings.apiKey,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(settings: Settings): Promise<{ status: string }> {
  return request(settings, "/health");
}

export async function getRecommendation(settings: Settings): Promise<Recommendation> {
  return request(settings, `/recommend/context?user_id=${encodeURIComponent(settings.userId)}`);
}

export async function getRecentEvents(settings: Settings, limit = 24): Promise<{ events: RecentEvent[] }> {
  return request(settings, `/me/recent-events?user_id=${encodeURIComponent(settings.userId)}&limit=${limit}`);
}

export async function getSources(settings: Settings): Promise<SourcesResponse> {
  return request(settings, `/me/sources?user_id=${encodeURIComponent(settings.userId)}`);
}

export async function getDashboard(settings: Settings, limit = 24): Promise<DashboardResponse> {
  return request(settings, `/me/dashboard?user_id=${encodeURIComponent(settings.userId)}&limit=${limit}`);
}

export async function sendFeedback(settings: Settings, topic: Topic, action: "like" | "skip"): Promise<void> {
  await request(settings, "/feedback", {
    method: "POST",
    body: JSON.stringify({
      user_id: settings.userId,
      recommendation_topic: topic,
      action
    })
  });
}

export async function loadDashboard(settings: Settings) {
  const dashboard = await getDashboard(settings);

  return {
    recommendation: dashboard.recommendation,
    events: dashboard.events,
    sources: dashboard.sources
  };
}
