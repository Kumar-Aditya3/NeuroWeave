# Quick Start - NeuroWeave Portable

## Prerequisites
- Windows 10+ (64-bit)
- Python 3.9+ (download from python.org, check "Add to PATH")

## Installation (One Time)

1. **Copy the NeuroWeave folder** to your PC
2. **Double-click `setup_portable.bat`** 
   - Wait for completion (5-15 minutes)
   - Shows "[OK] Setup Complete!" when done

## Running NeuroWeave

### Option A: Everything in One Click
```
Double-click: run_all.bat
```
Opens both backend and desktop automatically.

### Option B: Manual Start
1. **Terminal 1** - Start backend:
   ```
   Double-click: run_backend.bat
   Wait for: "Uvicorn running on http://127.0.0.1:8000"
   ```

2. **Terminal 2** - Start desktop:
   ```
   Double-click: run_desktop.bat
   Desktop app launches
   ```

## Default Settings
- **Backend:** http://127.0.0.1:8000
- **API Key:** dev-local-key
- **Database:** backend/data.db (auto-created)
- **Model:** Stable Diffusion XL (downloads ~7GB on first use)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Install Python, restart PC, try again |
| Port 8000 already in use | Change port in `run_backend.bat` |
| Desktop can't connect | Make sure backend window is open |
| Slow generation | First run downloads 7GB model, subsequent runs are faster |

## Detailed Guide
See `PORTABLE_SETUP.md` for complete documentation.

## File Structure
```
NeuroWeave/
├── backend/              (Server - http://127.0.0.1:8000)
├── desktop/dist/         (Desktop app)
├── setup_portable.bat    (Initial setup)
├── run_all.bat          (Start both)
├── run_backend.bat      (Start server only)
├── run_desktop.bat      (Start app only)
└── PORTABLE_SETUP.md    (Full guide)
```

**Version:** 0.1.0 | **Platform:** Windows x64 | **Date:** April 2026
