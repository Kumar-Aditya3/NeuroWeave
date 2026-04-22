import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("neuroWeaveSettings", {
  get: () => ipcRenderer.invoke("settings:get"),
  set: (settings: unknown) => ipcRenderer.invoke("settings:set", settings)
});
