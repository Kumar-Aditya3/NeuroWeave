import { app, BrowserWindow, ipcMain } from "electron";
import { execFile } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import os from "node:os";
import path from "node:path";
import { URL } from "node:url";

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

function downloadFile(url: string, destination: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const transport = parsed.protocol === "http:" ? http : https;

    const request = transport.get(url, (response) => {
      const status = response.statusCode ?? 0;
      if ([301, 302, 303, 307, 308].includes(status)) {
        const location = response.headers.location;
        response.resume();
        if (!location) {
          reject(new Error("Wallpaper redirect missing location header"));
          return;
        }
        const redirected = new URL(location, url).toString();
        downloadFile(redirected, destination).then(resolve).catch(reject);
        return;
      }

      if (status < 200 || status >= 300) {
        response.resume();
        reject(new Error(`Wallpaper download failed with status ${status}`));
        return;
      }

      const file = fs.createWriteStream(destination);
      response.pipe(file);
      file.on("finish", () => {
        file.close();
        resolve();
      });
      file.on("error", (error) => {
        file.close();
        reject(error);
      });
    });

    request.on("error", reject);
  });
}

function setWindowsWallpaper(imagePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const escapedPath = imagePath.replace(/'/g, "''");
    const command = [
      "$signature = @'",
      "using System.Runtime.InteropServices;",
      "public class NativeWallpaper {",
      "  [DllImport(\"user32.dll\", SetLastError=true)]",
      "  public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);",
      "}",
      "'@;",
      "Add-Type $signature -ErrorAction SilentlyContinue;",
      `$ok = [NativeWallpaper]::SystemParametersInfo(20, 0, '${escapedPath}', 3);`,
      "if (-not $ok) { exit 1 }",
    ].join(" ");

    execFile(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
      (error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      }
    );
  });
}

ipcMain.handle("wallpaper:set", async (_event, payload: { previewUrl?: string; cachedPath?: string | null }) => {
  if (process.platform !== "win32") {
    return { ok: false, message: "Setting wallpaper is currently supported on Windows only." };
  }

  try {
    let localPath = "";
    if (payload.cachedPath && fs.existsSync(payload.cachedPath)) {
      localPath = payload.cachedPath;
    } else if (payload.previewUrl) {
      const tempDir = path.join(os.tmpdir(), "neuroweave");
      fs.mkdirSync(tempDir, { recursive: true });
      localPath = path.join(tempDir, "current_wallpaper.jpg");
      await downloadFile(payload.previewUrl, localPath);
    } else {
      return { ok: false, message: "No wallpaper URL or cache path was provided." };
    }

    await setWindowsWallpaper(localPath);
    return { ok: true, message: "Desktop wallpaper updated.", path: localPath };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Failed to set wallpaper.",
    };
  }
});

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
