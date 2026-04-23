import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  Clapperboard,
  Gauge,
  HardDrive,
  Heart,
  ImagePlus,
  LayoutDashboard,
  MonitorSmartphone,
  MoonStar,
  Music2,
  RefreshCcw,
  Settings as SettingsIcon,
  SlidersHorizontal,
  Sparkles,
  Wallpaper,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { loadDashboard, sendFeedback } from "./api/client";
import type { DashboardData, RecentEvent, Settings, Topic } from "./types";

const navItems = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "activity", label: "Activity", icon: Activity },
  { id: "devices", label: "Devices", icon: MonitorSmartphone },
  { id: "tuning", label: "Tuning", icon: SlidersHorizontal },
  { id: "settings", label: "Settings", icon: SettingsIcon },
] as const;

const topicLabels: Record<Topic, string> = {
  tech: "Tech",
  education: "Education",
  anime: "Anime",
  fitness: "Fitness",
  philosophy: "Philosophy",
  "self-help": "Self-help",
  news: "News",
  unknown: "Unknown",
};

function App() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [activeView, setActiveView] = useState<(typeof navItems)[number]["id"]>("overview");
  const [dashboard, setDashboard] = useState<DashboardData>({
    online: false,
    lastSync: null,
    recommendation: null,
    events: [],
    sources: [],
  });
  const [feedbackState, setFeedbackState] = useState("");

  const refresh = useCallback(async () => {
    if (!settings) return;
    try {
      const data = await loadDashboard(settings);
      setDashboard({
        online: true,
        lastSync: new Date().toLocaleTimeString(),
        recommendation: data.recommendation,
        events: data.events,
        sources: data.sources,
      });
    } catch (error) {
      setDashboard((current) => ({
        ...current,
        online: false,
        error: error instanceof Error ? error.message : "Backend unreachable",
      }));
    }
  }, [settings]);

  useEffect(() => {
    window.neuroWeaveSettings.get().then(setSettings);
  }, []);

  useEffect(() => {
    if (!settings) return;
    refresh();
    const interval = window.setInterval(refresh, settings.refreshIntervalSeconds * 1000);
    return () => window.clearInterval(interval);
  }, [refresh, settings]);

  const filteredEvents = useMemo(() => {
    if (!settings) return dashboard.events;
    return dashboard.events.filter((event) => {
      if (!settings.privacy.showBrowser && event.event_type === "browser_tab") return false;
      if (!settings.privacy.showApps && ["active_window", "game"].includes(event.event_type)) return false;
      if (!settings.privacy.showOcr && event.event_type === "ocr_text") return false;
      return true;
    });
  }, [dashboard.events, settings]);

  async function updateSettings(next: Partial<Settings>) {
    const updated = await window.neuroWeaveSettings.set(next);
    setSettings(updated);
  }

  async function handleFeedback(action: "like" | "skip", label: string) {
    if (!settings || !dashboard.recommendation) return;
    await sendFeedback(settings, dashboard.recommendation.primary_topic, action);
    setFeedbackState(label);
    setTimeout(() => setFeedbackState(""), 1600);
  }

  if (!settings) {
    return <div className="boot">Loading NeuroWeave</div>;
  }

  const recommendation = dashboard.recommendation;
  const primaryTopic = recommendation?.primary_topic ?? "unknown";
  const vibe = recommendation?.vibe ?? "balanced";

  return (
    <div className={`app ${settings.themeMode} ${settings.consoleDensity}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">NW</div>
          <div>
            <strong>NeuroWeave</strong>
            <span>Vibe Console</span>
          </div>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={activeView === item.id ? "active" : ""}
                key={item.id}
                onClick={() => setActiveView(item.id)}
                type="button"
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="console">
        <header className="topbar">
          <div>
            <span className="eyebrow">User</span>
            <strong>{settings.userId}</strong>
          </div>
          <div className={dashboard.online ? "status online" : "status offline"}>
            {dashboard.online ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            {dashboard.online ? "Backend online" : "Backend offline"}
          </div>
          <div className="topMetric">
            <span>{dashboard.sources.length}</span>
            active devices
          </div>
          <div className="topMetric">
            <span>{dashboard.lastSync ?? "Never"}</span>
            last sync
          </div>
          <button className="iconButton" onClick={refresh} type="button" title="Refresh">
            <RefreshCcw size={17} />
          </button>
        </header>

        {activeView === "overview" && (
          <section className="view overview">
            <div className="stateStrip">
              <StatePill icon={Brain} label="Model" value={recommendation?.classifier_mode ?? settings.classifierMode} />
              <StatePill icon={Gauge} label="Topic" value={topicLabels[primaryTopic]} />
              <StatePill icon={MoonStar} label="Vibe" value={vibe} />
              <StatePill icon={Wallpaper} label="Style" value={settings.wallpaperStyle} />
            </div>

            <div className="grid heroGrid">
              <section className="heroPanel wallpaperPanel">
                <div className="wallpaperPreview">
                  {recommendation?.wallpaper_preview_url ? (
                    <img alt="Wallpaper preview" src={recommendation.wallpaper_preview_url} />
                  ) : (
                    <div className="placeholderVisual">
                      <Wallpaper size={30} />
                      <span>Waiting for wallpaper suggestion</span>
                    </div>
                  )}
                </div>
                <div className="wallpaperMeta">
                  <div>
                    <span className="eyebrow">Wallpaper mood</span>
                    <h1>{topicLabels[primaryTopic]} / {vibe}</h1>
                    <p>{recommendation?.wallpaper_query ?? "Building an aesthetic from your recent activity."}</p>
                  </div>
                  <div className="paletteRow">
                    {(recommendation?.wallpaper_palette ?? []).map((color) => (
                      <span className="swatch" key={color} style={{ background: color }} />
                    ))}
                  </div>
                  <div className="altRow">
                    {(recommendation?.wallpaper_alternates ?? []).slice(0, 3).map((item, index) => (
                      <img alt={`Alternate wallpaper ${index + 1}`} key={item.preview_url} src={item.preview_url} />
                    ))}
                  </div>
                  <div className="buttonRow">
                    <button onClick={refresh} type="button">
                      <ImagePlus size={16} /> Refresh aesthetic
                    </button>
                    <button disabled type="button">
                      <Wallpaper size={16} /> Set as desktop
                    </button>
                  </div>
                  <p className="sourceLine">Source: {recommendation?.wallpaper_source ?? "Curated feed"}</p>
                </div>
              </section>

              <section className="panel recommendationBand">
                <div className="panelHeader">
                  <h2>Recommendation Band</h2>
                  <Sparkles size={18} />
                </div>
                <div className="grid three">
                  <InsightCard icon={Music2} label="Music mood" value={recommendation?.music_mood ?? "Waiting"} />
                  <InsightCard icon={Sparkles} label="Quote style" value={recommendation?.quote_style ?? "Waiting"} />
                  <InsightCard icon={Clapperboard} label="Wallpaper tags" value={recommendation?.wallpaper_tags.join(", ") ?? "Waiting"} />
                </div>
              </section>
            </div>

            <div className="grid explanationGrid">
              <section className="panel">
                <div className="panelHeader">
                  <h2>Why this was chosen</h2>
                  <Brain size={18} />
                </div>
                <p className="explain">{recommendation?.explanation ?? "Reasoning will appear once the backend responds."}</p>
                <div className="feedbackRow">
                  <button onClick={() => handleFeedback("like", "Marked as felt right")} type="button">
                    <Heart size={16} /> Felt right
                  </button>
                  <button onClick={() => handleFeedback("skip", "Marked as not me")} type="button">
                    <XCircle size={16} /> Not me
                  </button>
                  <button onClick={() => handleFeedback("skip", "Intensity feedback saved")} type="button">
                    <AlertTriangle size={16} /> Too intense
                  </button>
                </div>
                {feedbackState && <p className="success">{feedbackState}</p>}
                {!dashboard.online && dashboard.error && <p className="error">{dashboard.error}</p>}
              </section>

              <EventList events={filteredEvents.slice(0, 8)} title="Latest activity" />
            </div>
          </section>
        )}

        {activeView === "activity" && <EventList events={filteredEvents} title="Activity stream" large />}
        {activeView === "devices" && <Devices sources={dashboard.sources} events={filteredEvents} />}
        {activeView === "tuning" && <Tuning settings={settings} updateSettings={updateSettings} />}
        {activeView === "settings" && <SettingsView settings={settings} updateSettings={updateSettings} />}
      </main>
    </div>
  );
}

function StatePill({ icon: Icon, label, value }: { icon: typeof Brain; label: string; value: string }) {
  return (
    <section className="statePill">
      <Icon size={16} />
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function InsightCard({ icon: Icon, label, value }: { icon: typeof Wallpaper; label: string; value: string }) {
  return (
    <section className="metricCard">
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
    </section>
  );
}

function EventList({ events, title, large = false }: { events: RecentEvent[]; title: string; large?: boolean }) {
  return (
    <section className={`panel ${large ? "largePanel" : ""}`}>
      <div className="panelHeader">
        <h2>{title}</h2>
        <Activity size={18} />
      </div>
      <div className="eventList">
        {events.length === 0 && <p className="empty">No matching activity yet.</p>}
        {events.map((event) => (
          <article className="eventRow" key={event.id}>
            <div>
              <strong>{event.title ?? "Untitled event"}</strong>
              <span>
                {event.client_name ?? "Unknown device"} / {event.event_type} / {event.classifier_mode ?? "n/a"}
              </span>
            </div>
            <time>{new Date(event.created_at).toLocaleTimeString()}</time>
          </article>
        ))}
      </div>
    </section>
  );
}

function Devices({ sources, events }: { sources: DashboardData["sources"]; events: RecentEvent[] }) {
  const mix = {
    browser: events.filter((event) => event.event_type === "browser_tab").length,
    apps: events.filter((event) => ["active_window", "game"].includes(event.event_type)).length,
    ocr: events.filter((event) => event.event_type === "ocr_text").length,
  };

  return (
    <section className="panel largePanel">
      <div className="panelHeader">
        <h2>Devices</h2>
        <HardDrive size={18} />
      </div>
      <div className="mixRow">
        <StatePill icon={Activity} label="Browser-heavy" value={String(mix.browser)} />
        <StatePill icon={MonitorSmartphone} label="App-heavy" value={String(mix.apps)} />
        <StatePill icon={Sparkles} label="OCR-active" value={String(mix.ocr)} />
      </div>
      <div className="deviceGrid">
        {sources.length === 0 && <p className="empty">No devices have checked in yet.</p>}
        {sources.map((source) => (
          <article className="deviceCard" key={source.device_id}>
            <MonitorSmartphone size={20} />
            <strong>{source.client_name}</strong>
            <span>{source.device_id}</span>
            <time>Last seen {new Date(source.last_seen_at).toLocaleString()}</time>
          </article>
        ))}
      </div>
    </section>
  );
}

function Tuning({ settings, updateSettings }: { settings: Settings; updateSettings: (next: Partial<Settings>) => void }) {
  return (
    <section className="panel largePanel">
      <div className="panelHeader">
        <h2>Tuning</h2>
        <SlidersHorizontal size={18} />
      </div>
      <div className="tuningLayout">
        <section className="subPanel">
          <h3>Model</h3>
          <label>
            Classifier mode
            <select
              value={settings.classifierMode}
              onChange={(event) => updateSettings({ classifierMode: event.target.value as Settings["classifierMode"] })}
            >
              <option value="embedding_primary">Embedding primary</option>
              <option value="keyword_fallback">Keyword fallback</option>
            </select>
          </label>
          <label>
            Recommendation intensity
            <select
              value={settings.recommendationIntensity}
              onChange={(event) => updateSettings({ recommendationIntensity: event.target.value as Settings["recommendationIntensity"] })}
            >
              <option value="calm">Calm</option>
              <option value="balanced">Balanced</option>
              <option value="strong">Strong</option>
            </select>
          </label>
        </section>

        <section className="subPanel">
          <h3>Wallpaper</h3>
          <label>
            Wallpaper style
            <select
              value={settings.wallpaperStyle}
              onChange={(event) => updateSettings({ wallpaperStyle: event.target.value as Settings["wallpaperStyle"] })}
            >
              <option value="minimal">Minimal</option>
              <option value="cinematic">Cinematic</option>
              <option value="warm">Warm</option>
              <option value="neon">Neon</option>
              <option value="editorial">Editorial</option>
            </select>
          </label>
          {Object.entries(settings.topicWeights).map(([topic, value]) => (
            <label className="sliderLabel" key={topic}>
              <span>{topicLabels[topic as Topic]} bias: {value}</span>
              <input
                type="range"
                min="0"
                max="100"
                value={value}
                onChange={(event) =>
                  updateSettings({
                    topicWeights: {
                      ...settings.topicWeights,
                      [topic]: Number(event.target.value),
                    },
                  })
                }
              />
            </label>
          ))}
        </section>

        <section className="subPanel">
          <h3>Privacy</h3>
          <div className="toggleStack">
            <Toggle label="Show browser activity" checked={settings.privacy.showBrowser} onChange={(value) => updateSettings({ privacy: { ...settings.privacy, showBrowser: value } })} />
            <Toggle label="Show app/game activity" checked={settings.privacy.showApps} onChange={(value) => updateSettings({ privacy: { ...settings.privacy, showApps: value } })} />
            <Toggle label="Show OCR activity" checked={settings.privacy.showOcr} onChange={(value) => updateSettings({ privacy: { ...settings.privacy, showOcr: value } })} />
          </div>
        </section>
      </div>
    </section>
  );
}

function SettingsView({ settings, updateSettings }: { settings: Settings; updateSettings: (next: Partial<Settings>) => void }) {
  return (
    <section className="panel largePanel">
      <div className="panelHeader">
        <h2>Settings</h2>
        <SettingsIcon size={18} />
      </div>
      <div className="settingsGrid">
        <label>
          Backend URL
          <input value={settings.backendUrl} onChange={(event) => updateSettings({ backendUrl: event.target.value })} />
        </label>
        <label>
          API key
          <input type="password" value={settings.apiKey} onChange={(event) => updateSettings({ apiKey: event.target.value })} />
        </label>
        <label>
          User ID
          <input value={settings.userId} onChange={(event) => updateSettings({ userId: event.target.value })} />
        </label>
        <label>
          Refresh interval
          <select
            value={settings.refreshIntervalSeconds}
            onChange={(event) => updateSettings({ refreshIntervalSeconds: Number(event.target.value) })}
          >
            <option value={3}>3 seconds</option>
            <option value={5}>5 seconds</option>
            <option value={10}>10 seconds</option>
            <option value={30}>30 seconds</option>
          </select>
        </label>
        <label>
          Density
          <select
            value={settings.consoleDensity}
            onChange={(event) => updateSettings({ consoleDensity: event.target.value as Settings["consoleDensity"] })}
          >
            <option value="comfortable">Comfortable</option>
            <option value="compact">Compact</option>
          </select>
        </label>
        <label>
          Theme
          <select value={settings.themeMode} onChange={(event) => updateSettings({ themeMode: event.target.value as Settings["themeMode"] })}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
      </div>
    </section>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

export default App;
