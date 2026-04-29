# NeuroWeave Portable Setup Guide

This guide explains how to set up NeuroWeave on another PC by simply copying files.

## What You Need on the Target PC

- **Windows 10 or later** (64-bit)
- **Python 3.9+** installed and in PATH (download from https://www.python.org)
- **Internet connection** (for initial dependency download)
- At least 10 GB free disk space (for virtual environment and models)

## Setup Instructions

### Step 1: Copy the NeuroWeave Folder

Copy the entire `NeuroWeave` folder to your target PC. You can place it anywhere, for example:
- `C:\NeuroWeave`
- `D:\NeuroWeave`
- Your user folder

The folder should contain:
```
NeuroWeave/
├── backend/              (FastAPI server)
├── desktop/              (Electron app)
├── agent/                (Windows activity monitor)
├── setup_portable.bat    (One-time setup script)
├── run_backend.bat       (Start backend server)
├── run_desktop.bat       (Launch desktop app)
├── requirements.txt      (Dependencies list)
└── ... (other folders)
```

### Step 2: Run Initial Setup (One Time)

1. Open the copied `NeuroWeave` folder
2. Double-click `setup_portable.bat`
3. The script will:
   - Check if Python is installed
   - Create a virtual environment in `backend\.venv`
   - Download and install all dependencies
   - Initialize the database if needed

**Note:** This may take 5-15 minutes depending on your internet speed (especially for `torch` and `diffusers` downloads).

### Step 3: Start the Backend

1. Double-click `run_backend.bat`
2. Wait for the message: `Uvicorn running on http://127.0.0.1:8000`
3. You can now access API docs at http://127.0.0.1:8000/docs

**Important:** Keep this window open while using the desktop app.

### Step 4: Launch the Desktop App

1. Open a new command prompt/PowerShell window in the NeuroWeave folder
2. Double-click `run_desktop.bat`
3. The desktop application will launch

The app will connect to the backend running on `http://127.0.0.1:8000`.

## Portable Architecture

### Backend (`backend/`)
- FastAPI server with Pydantic models
- Wallpaper generation (diffusion-based with procedural fallback)
- Activity profiling and recommendation engine
- Embedded SQLite database (`backend/data.db`)
- Virtual environment: `backend\.venv` (created during setup)

**Key Scripts:**
- `run_backend.bat` - Start the server on localhost:8000

### Desktop (`desktop/dist/`)
- Electron-based React application
- Communicates with backend via HTTP
- Can set wallpapers on Windows

**Key Files:**
- `NeuroWeave.exe` or `NeuroWeave Setup 0.1.0.exe` - Runnable application

### Agent (`agent/`)
- Windows system tray activity monitor
- Tracks active window, browser tabs, games
- Sends data to backend
- Optional: Run `agent\run.py` to start the watcher

## Configuration

### API Keys (Optional)
By default, the backend uses `dev-local-key`. To change:

Edit `run_backend.bat` and change:
```batch
set "NEUROWEAVE_API_KEYS=dev-local-key"
```

### Backend URL
The desktop app expects the backend at `http://127.0.0.1:8000`. This is configured in the desktop app settings.

### Diffusion Model
The backend uses `stabilityai/stable-diffusion-xl-base-1.0` by default. First run will download the model (~7 GB).

To use a different model, set environment variable before running `run_backend.bat`:
```batch
set DIFFUSION_MODEL_ID=different-model-id
```

### Inference Settings
Configure in `run_backend.bat` using environment variables:
- `DIFFUSION_STEPS=30` (more steps = better quality but slower)
- `DIFFUSION_GUIDANCE_SCALE=7.5` (creative control)
- `DIFFUSION_TIMEOUT_SECONDS=40` (timeout for slow GPUs)

## Folder Structure Overview

```
NeuroWeave/
├── backend/                    # FastAPI server
│   ├── app/
│   │   ├── main.py             # Entry point
│   │   ├── models.py           # Pydantic schemas
│   │   ├── wallpapers/         # Wallpaper generation
│   │   │   ├── diffusion.py    # Diffusion pipeline
│   │   │   ├── procedural.py   # Fallback generator
│   │   │   ├── providers.py    # Provider abstraction
│   │   │   ├── service.py      # Orchestration
│   │   │   └── cache.py        # Image caching
│   │   └── ... (other modules)
│   ├── data.db                 # SQLite database (created on first run)
│   ├── wallpaper_cache/        # Generated wallpaper cache
│   ├── requirements.txt        # Python dependencies
│   └── .venv/                  # Virtual environment (created by setup)
│
├── desktop/                    # Electron + React app
│   ├── dist/
│   │   ├── NeuroWeave.exe      # Packaged application
│   │   ├── assets/             # CSS, JS bundles
│   │   └── ... (other files)
│   ├── src/
│   │   ├── App.tsx             # Main React component
│   │   └── ... (other components)
│   └── electron/               # Electron main process
│
├── agent/                      # Windows activity monitor
│   └── run.py                  # Start the agent
│
├── setup_portable.bat          # ONE-TIME setup script
├── run_backend.bat             # Start backend server
├── run_desktop.bat             # Launch desktop app
└── README.md                   # Main documentation
```

## Troubleshooting

### "Python not found"
- Ensure Python 3.9+ is installed
- During Python installation, check "Add Python to PATH"
- Restart your computer after installing Python

### Backend won't start
```
ERROR: Address already in use
```
- Port 8000 is occupied
- Edit `run_backend.bat` and change `--port 8000` to another port (e.g., `--port 8001`)
- Then update desktop app settings to use the new URL

### Desktop app can't connect to backend
- Verify backend is running with `run_backend.bat`
- Check that it shows "Uvicorn running on http://127.0.0.1:8000"
- In desktop app settings, verify Backend URL is `http://127.0.0.1:8000`

### Slow or missing wallpaper generation
- Diffusion model downloads on first use (~7 GB)
- Check backend logs for model loading messages
- GPU memory requirements: ~6 GB VRAM (falls back to CPU if needed, slower)

### Database errors
- Delete `backend/data.db` to reset
- Re-run `setup_portable.bat` to reinitialize
- Database will auto-create if missing

## Advanced Usage

### Start Both Backend and Desktop Together
Create a batch file called `run_all.bat`:
```batch
@echo off
start run_backend.bat
timeout /t 3
start run_desktop.bat
```

Then double-click `run_all.bat` to launch everything.

### Run the Activity Agent
To collect activity data, start the agent in another window:
```batch
cd backend
.venv\Scripts\activate.bat
cd ..\agent
python run.py
```

### Access Backend API Directly
Once backend is running, visit:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

### Database Management
The SQLite database is at `backend/data.db`. You can inspect it with any SQLite viewer:
- VS Code SQLite extension
- DB Browser for SQLite (https://sqlitebrowser.org)
- Command line: `sqlite3 backend/data.db`

## Files to Exclude When Copying

Don't include these when copying to another PC (they can be recreated):
- `.git/` - Git repository metadata (only if you don't need version history)
- `.venv/` - Virtual environment (will be created by setup_portable.bat)
- `node_modules/` - Node packages (for desktop build only)
- `dist/` - Build outputs (already included in desktop/dist/)
- `build/` - Build artifacts
- `.env` - Local environment files (if any)
- `*.log` - Log files

## Minimal Copy Checklist

Before copying, ensure you have:
- ✅ `backend/` folder with `requirements.txt` and `sql/schema.sql`
- ✅ `desktop/dist/` folder with exe file
- ✅ `setup_portable.bat` in root
- ✅ `run_backend.bat` in root
- ✅ `run_desktop.bat` in root
- ✅ `agent/` folder (optional, for activity collection)

## Performance Notes

- **First startup:** Downloading diffusion model takes 10-30 minutes (one-time)
- **Generation speed:** 
  - With GPU (NVIDIA): ~10-20 seconds per image
  - With CPU: ~2-5 minutes per image
- **Memory usage:**
  - Backend: ~2 GB (without model), ~8 GB (with model)
  - Desktop: ~400 MB
  - Total: ~2.5-8.5 GB depending on GPU availability

## Getting Help

If something doesn't work:
1. Check that Python is installed: `python --version`
2. Check backend logs in `run_backend.bat` window for error messages
3. Open http://127.0.0.1:8000/docs to verify backend is responding
4. Check desktop app settings for correct backend URL

---

**Last Updated:** April 2026  
**Version:** 0.1.0  
**Architecture:** Portable Windows x64
