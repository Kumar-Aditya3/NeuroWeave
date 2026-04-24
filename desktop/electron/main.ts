import { app, BrowserWindow, ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";

type ConsoleDensity = "comfortable" | "compact";
type ThemeMode = "dark" | "light";
type Intensity = "calm" | "balanced" | "strong";
type ClassifierMode = "embedding_primary" | "keyword_fallback";
type WallpaperStyle = "minimal" | "cinematic" | "warm" | "neon" | "editorial";
type WallpaperProvider = "curated_unsplash" | "generated_future";

type Settings = {
  backendUrl: string;
  apiKey: string;
  userId: string;
  refreshIntervalSeconds: number;
  themeMode: ThemeMode;
  consoleDensity: ConsoleDensity;
  recommendationIntensity: Intensity;
  classifierMode: ClassifierMode;
  wallpaperStyle: WallpaperStyle;
  wallpaperProvider: WallpaperProvider;
  topicWeights: Record<string, number>;
  privacy: {
    showBrowser: boolean;
    showApps: boolean;
    showOcr: boolean;
  };
};

const defaults: Settings = {
  backendUrl: "http://127.0.0.1:8000",
  apiKey: "dev-local-key",
  userId: "kumar",
  refreshIntervalSeconds: 5,
  themeMode: "dark",
  consoleDensity: "comfortable",
  recommendationIntensity: "balanced",
  classifierMode: "embedding_primary",
  wallpaperStyle: "minimal",
  wallpaperProvider: "curated_unsplash",
  topicWeights: {
    tech: 50,
    education: 50,
    anime: 50,
    fitness: 50,
    philosophy: 50,
    "self-help": 50,
    news: 50,
    unknown: 50
  },
  privacy: {
    showBrowser: true,
    showApps: true,
    showOcr: true
  }
};

function settingsPath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function readSettings(): Settings {
  try {
    const raw = fs.readFileSync(settingsPath(), "utf-8");
    return { ...defaults, ...JSON.parse(raw) };
  } catch {
    writeSettings(defaults);
    return defaults;
  }
}

function writeSettings(settings: Settings) {
  fs.mkdirSync(app.getPath("userData"), { recursive: true });
  fs.writeFileSync(settingsPath(), JSON.stringify(settings, null, 2), "utf-8");
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 1080,
    minHeight: 720,
    backgroundColor: "#101211",
    title: "NeuroWeave",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    win.loadURL(devServerUrl);
  } else {
    win.loadFile(path.join(__dirname, "../dist-renderer/index.html"));
  }
}

ipcMain.handle("settings:get", () => readSettings());
ipcMain.handle("settings:set", (_event, nextSettings: Partial<Settings>) => {
  const settings = { ...readSettings(), ...nextSettings };
  writeSettings(settings);
  return settings;
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
