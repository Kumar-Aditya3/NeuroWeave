const DEFAULTS = {
  trackingEnabled: false,
  userId: "kumar",
  deviceId: "",
  clientName: "Browser",
  backendUrl: "http://127.0.0.1:8000",
  apiKey: "dev-local-key"
};

const blockedSchemes = ["chrome://", "opera://", "edge://", "about:", "file://"];
const lastSentByTab = new Map();

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

async function sendTabEvent(tab) {
  const settings = await getSettings();
  if (!settings.trackingEnabled || !isTrackableUrl(tab.url)) return;

  const lastKey = lastSentByTab.get(tab.id);
  const currentKey = `${tab.url}|${tab.title || ""}`;
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
    timestamp: new Date().toISOString()
  };

  try {
    const response = await fetch(`${settings.backendUrl}/ingest/activity`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": settings.apiKey
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      console.warn("NeuroWeave ingest failed", response.status, await response.text());
    }
  } catch (error) {
    console.warn("NeuroWeave backend unreachable", error);
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  await getSettings();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    sendTabEvent(tab);
  }
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId);
  sendTabEvent(tab);
});
