# NeuroWeave Desktop

NeuroWeave Desktop is the Vibe Console for the local FastAPI backend.

## Development

```bash
npm install
npm run dev
```

The desktop app expects the backend to be running at:

```text
http://127.0.0.1:8000
```

Default API key:

```text
dev-local-key
```

## Build

```bash
npm run build
```

## Windows Installer

```bash
npm run dist
```

Installer output:

```text
desktop/dist/NeuroWeave Setup 0.1.0.exe
```

## Settings

Settings are stored locally by Electron in the app user data folder. The app stores:

- backend URL
- API key
- user ID
- refresh interval
- theme mode
- console density
- recommendation intensity
- local topic tuning weights
- local display privacy toggles
