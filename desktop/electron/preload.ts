import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("neuroWeaveSettings", {
  get: () => ipcRenderer.invoke("settings:get"),
  set: (settings: unknown) => ipcRenderer.invoke("settings:set", settings)
});

contextBridge.exposeInMainWorld("neuroWeaveDesktop", {
  setWallpaper: (payload: { previewUrl?: string; cachedPath?: string | null }) =>
    ipcRenderer.invoke("wallpaper:set", payload),
});
