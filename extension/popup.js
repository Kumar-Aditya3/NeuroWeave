const DEFAULTS = {
  trackingEnabled: false,
  userId: "kumar",
  clientName: "Browser",
  backendUrl: "http://127.0.0.1:8000",
  apiKey: "dev-local-key",
  cloudIngestEnabled: false,
  cloudIngestUrl: "",
  cloudIngestKey: ""
};

const fields = {
  trackingEnabled: document.querySelector("#trackingEnabled"),
  userId: document.querySelector("#userId"),
  clientName: document.querySelector("#clientName"),
  backendUrl: document.querySelector("#backendUrl"),
  apiKey: document.querySelector("#apiKey"),
  cloudIngestEnabled: document.querySelector("#cloudIngestEnabled"),
  cloudIngestUrl: document.querySelector("#cloudIngestUrl"),
  cloudIngestKey: document.querySelector("#cloudIngestKey")
};

const status = document.querySelector("#status");

async function loadSettings() {
  const settings = await chrome.storage.local.get(DEFAULTS);
  fields.trackingEnabled.checked = settings.trackingEnabled;
  fields.userId.value = settings.userId;
  fields.clientName.value = settings.clientName;
  fields.backendUrl.value = settings.backendUrl;
  fields.apiKey.value = settings.apiKey;
  fields.cloudIngestEnabled.checked = settings.cloudIngestEnabled;
  fields.cloudIngestUrl.value = settings.cloudIngestUrl;
  fields.cloudIngestKey.value = settings.cloudIngestKey;
}

async function saveSettings() {
  await chrome.storage.local.set({
    trackingEnabled: fields.trackingEnabled.checked,
    userId: fields.userId.value.trim() || DEFAULTS.userId,
    clientName: fields.clientName.value.trim() || DEFAULTS.clientName,
    backendUrl: fields.backendUrl.value.trim().replace(/\/$/, "") || DEFAULTS.backendUrl,
    apiKey: fields.apiKey.value.trim() || DEFAULTS.apiKey,
    cloudIngestEnabled: fields.cloudIngestEnabled.checked,
    cloudIngestUrl: fields.cloudIngestUrl.value.trim(),
    cloudIngestKey: fields.cloudIngestKey.value.trim()
  });
  status.textContent = "Saved";
  setTimeout(() => {
    status.textContent = "";
  }, 1200);
}

Object.values(fields).forEach((field) => {
  field.addEventListener("change", saveSettings);
});

loadSettings();
