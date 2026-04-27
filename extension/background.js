const DEFAULTS = {
  trackingEnabled: false,
  userId: "kumar",
  deviceId: "",
  clientName: "Browser",
  backendUrl: "http://127.0.0.1:8000",
  apiKey: "dev-local-key",
  cloudIngestEnabled: false,
  cloudIngestUrl: "",
  cloudIngestKey: ""
};

const blockedSchemes = ["chrome://", "opera://", "edge://", "about:", "file://"];
const lastSentByTab = new Map();
let activeTabState = null;

async function getSettings() {
  const settings = await chrome.storage.local.get(DEFAULTS);
  if (!settings.deviceId) {
    settings.deviceId = crypto.randomUUID();
    await chrome.storage.local.set({ deviceId: settings.deviceId });
  }
  return settings;
}

function isTrackableUrl(url) {
  if (!url) return false;
  return !blockedSchemes.some((scheme) => url.startsWith(scheme));
}

function hostnameFor(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

async function sendTabEvent(tab, durationSeconds = null) {
  const settings = await getSettings();
  if (!settings.trackingEnabled || !isTrackableUrl(tab.url)) return;

  const lastKey = lastSentByTab.get(tab.id);
  const currentKey = `${tab.url}|${tab.title || ""}|${durationSeconds ?? "open"}`;
  if (lastKey === currentKey) return;
  lastSentByTab.set(tab.id, currentKey);

  const payload = {
    user_id: settings.userId,
    device_id: settings.deviceId,
    client_name: settings.clientName,
    source: "browser_tab",
    event_type: "browser_tab",
    url: tab.url,
    title: tab.title || tab.url,
    category: "browsing",
    duration_seconds: durationSeconds,
    content_text: `browser activity on ${hostnameFor(tab.url)}`,
    timestamp: new Date().toISOString()
  };

  let backendOk = false;
  try {
    const response = await fetch(`${settings.backendUrl}/ingest/activity`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": settings.apiKey
      },
      body: JSON.stringify(payload)
    });
    backendOk = response.ok;
    if (!response.ok) {
      console.warn("NeuroWeave ingest failed", response.status, await response.text());
    }
  } catch (error) {
    console.warn("NeuroWeave backend unreachable", error);
  }

  if (backendOk) {
    return;
  }
  if (!settings.cloudIngestEnabled || !settings.cloudIngestUrl) {
    return;
  }

  try {
    const headers = {
      "Content-Type": "application/json"
    };
    if (settings.cloudIngestKey) {
      headers["X-Ingest-Key"] = settings.cloudIngestKey;
    }
    const response = await fetch(settings.cloudIngestUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      console.warn("Cloud ingest failed", response.status, await response.text());
    }
  } catch (error) {
    console.warn("Cloud ingest unreachable", error);
  }
}

async function flushActiveTab() {
  if (!activeTabState) return;
  const durationSeconds = Math.floor((Date.now() - activeTabState.startedAt) / 1000);
  if (durationSeconds < 4) return;
  try {
    const tab = activeTabState.snapshot || await chrome.tabs.get(activeTabState.tabId);
    await sendTabEvent(tab, durationSeconds);
  } catch {
    // The tab may have closed before the service worker woke up.
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  await getSettings();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    activeTabState = { tabId, startedAt: Date.now(), snapshot: tab };
    sendTabEvent(tab, null);
  }
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  await flushActiveTab();
  const tab = await chrome.tabs.get(tabId);
  activeTabState = { tabId, startedAt: Date.now(), snapshot: tab };
  sendTabEvent(tab, null);
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  if (activeTabState?.tabId === tabId) {
    await flushActiveTab();
    activeTabState = null;
  }
});
