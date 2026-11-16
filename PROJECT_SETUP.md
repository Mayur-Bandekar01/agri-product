# Adinath Agri Services - Complete Project Setup Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [First Time Setup](#first-time-setup)
4. [Running the Application](#running-the-application)
5. [Creating Production Build](#creating-production-build)
6. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### Required Software:
1. **Python 3.10+** (Backend)
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Node.js 16+** (For production build only)
   - Download from: https://nodejs.org/
   - Includes npm package manager

3. **Windows OS** (Current configuration)
   - The project is configured for Windows
   - PowerShell or Command Prompt

---

## 📁 Project Structure

```
adinath-agri-services/
├── backend/                    # Python FastAPI backend
│   ├── app/                   # Application code
│   │   ├── routers/          # API endpoints
│   │   ├── database/         # Database management
│   │   ├── assets/           # Fonts, resources
│   │   ├── main.py           # Main application
│   │   ├── models.py         # Database models
│   │   ├── schemas.py        # API schemas
│   │   └── auth.py           # Authentication
│   ├── venv/                 # Python virtual environment
│   ├── adinath.db            # SQLite database
│   ├── backups/              # Database backups
│   └── desktop_server.py     # Desktop server launcher
├── frontend/                  # HTML/CSS/JS frontend
│   ├── index.html            # Main page
│   ├── css/                  # Stylesheets
│   ├── js/                   # JavaScript
│   └── icons/                # PWA icons
├── desktop/                   # Electron desktop wrapper
│   └── main.js               # Electron main process
├── start-backend.bat         # Quick start script
└── PROJECT_SETUP.md          # This file
```

---

## 🚀 First Time Setup

### Step 1: Verify Python Installation

Open PowerShell or Command Prompt and run:
```powershell
python --version
```
You should see: `Python 3.10.x` or higher

### Step 2: Verify Virtual Environment

The virtual environment is already created at `backend/venv/`. Verify it exists:
```powershell
cd "e:\agri project\adinath-agri-services-project (2)\adinath-agri-services-project\adinath-agri-services"
dir backend\venv
```

If the `venv` folder doesn't exist, create it:
```powershell
cd backend
python -m venv venv
```

### Step 3: Install Backend Dependencies

Activate the virtual environment and install packages:

**Using PowerShell:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Using Command Prompt:**
```cmd
cd backend
venv\Scripts\activate.bat
pip install -r requirements.txt
```

Required packages (auto-installed from requirements.txt):
- fastapi
- uvicorn
- sqlalchemy
- passlib
- python-jose
- python-multipart
- openpyxl (for CA export)

### Step 4: Verify Database

The database is already set up with 110 products. Verify it:
```powershell
# Check if database exists
dir backend\adinath.db

# Check database backups
dir backend\backups
```

### Step 5: Create Admin User (Already Done)

An admin user is already created with these credentials:
- **Username:** admin
- **Password:** admin123

To create additional users or reset password, run:
```powershell
cd backend
.\venv\Scripts\python.exe ..\create_admin.py
```

---

## ▶️ Running the Application

### Method 1: Using Batch File (Easiest)

1. Navigate to the project folder
2. Double-click: **`start-backend.bat`**
3. A terminal window will open showing the server status
4. Open browser: **http://localhost:8000**
5. Login with admin/admin123

### Method 2: Manual Start (PowerShell)

```powershell
# Navigate to project
cd "e:\agri project\adinath-agri-services-project (2)\adinath-agri-services-project\adinath-agri-services"

# Go to backend folder
cd backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Method 3: Manual Start (Command Prompt)

```cmd
rem Navigate to project
cd "e:\agri project\adinath-agri-services-project (2)\adinath-agri-services-project\adinath-agri-services"

rem Go to backend folder
cd backend

rem Activate virtual environment
venv\Scripts\activate.bat

rem Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### What You Should See:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX] using WatchFiles
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
2026-11-14 XX:XX:XX - app.main - INFO - === Adinath Agri Services Starting ===
2026-11-14 XX:XX:XX - app.main - INFO - Database integrity check passed
2026-11-14 XX:XX:XX - app.main - INFO - Application ready to serve requests
INFO:     Application startup complete.
```

### Accessing the Application:

1. **Main Application:** http://localhost:8000
2. **API Documentation:** http://localhost:8000/docs
3. **Health Check:** http://localhost:8000/api/health

---

## 📦 Creating Production Build

### Prerequisites for Building:
1. Install Node.js (if not already installed)
2. All backend dependencies installed

### Build Process:

1. **Run the build script:**
   ```powershell
   .\build-production.bat
   ```

2. **What happens during build:**
   - Backend is packaged with PyInstaller
   - Electron wrapper is built
   - Desktop installer is created
   - Output: `desktop/release/adinath-agri-setup-X.X.X.exe`

3. **Distribute the installer:**
   - Share the `.exe` file from `desktop/release/`
   - Users can install without Python/Node.js
   - Self-contained application with embedded database

---

## 🐛 Troubleshooting

### Problem: "Python not found"
**Solution:**
- Install Python 3.10+ from python.org
- During installation, check "Add Python to PATH"
- Restart PowerShell/Command Prompt

### Problem: "Module not found" errors
**Solution:**
- Make sure virtual environment is activated (you should see `(venv)` in prompt)
- Reinstall dependencies:
  ```powershell
  cd backend
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

### Problem: "Port 8000 already in use"
**Solution:**
- Another process is using port 8000
- Option 1: Close the other process
- Option 2: Use a different port:
  ```powershell
  python -m uvicorn app.main:app --reload --port 8001
  ```
  Then access at: http://localhost:8001

### Problem: "Cannot activate virtual environment (Execution Policy)"
**Solution (PowerShell):**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: "Database locked" error
**Solution:**
- Close all instances of the application
- Check if database file is open elsewhere
- Restore from backup if needed:
  ```powershell
  copy backend\backups\adinath_backup_YYYYMMDD_HHMMSS_startup.db backend\adinath.db
  ```

### Problem: Login fails
**Solution:**
- Reset admin password:
  ```powershell
  cd backend
  .\venv\Scripts\python.exe ..\create_admin.py
  ```
- New credentials will be displayed

### Problem: "Frontend not loading"
**Solution:**
- Clear browser cache (Ctrl+Shift+Delete)
- Try incognito/private browsing mode
- Verify backend is running (check terminal)
- Check browser console for errors (F12)

### Problem: Database is corrupted
**Solution:**
- Automatic backups are in `backend/backups/`
- Restore latest backup:
  ```powershell
  # Copy backup to main database location
  copy backend\backups\adinath_backup_YYYYMMDD_HHMMSS_startup.db backend\adinath.db
  ```

---

## 📊 Database Information

### Current Status:
- ✅ 110 products imported from PDF
- ✅ All products have HSN codes
- ✅ Fresh database ready for transactions

### Database Location:
- Main: `backend/adinath.db`
- Backups: `backend/backups/`

### Backup Strategy:
- Automatic backup on startup
- Automatic backup on shutdown
- Manual backup: Copy `adinath.db` file

### Reset Database:
To start fresh (will delete all data):
```powershell
cd backend
del adinath.db
python -c "from app.database.migrations import initialize_database; initialize_database()"
```

Then re-import products:
```powershell
.\venv\Scripts\python.exe ..\import_pdf_products.py --force
```

---

## 🔐 Default Credentials

### Admin User:
- **Username:** admin
- **Password:** admin123

### Security Note:
**⚠️ IMPORTANT:** Change the default password after first login in production!

To create additional users, use the frontend "User Management" feature or create via script.

---

## 📝 Log Files

### Application Logs:
- Location: `backend/app.log`
- Contains startup, errors, and request logs
- Useful for debugging issues

### View Logs:
```powershell
# View last 50 lines
Get-Content backend\app.log -Tail 50

# Monitor live (follow mode)
Get-Content backend\app.log -Wait -Tail 20
```

---

## 🔄 Regular Maintenance

### Weekly:
- Check log files for errors
- Verify database backups exist
- Test CA export functionality

### Monthly:
- Update dependencies (if needed)
- Review and clean old backups
- Test production build process

### As Needed:
- Import new products
- Create database backups before major changes
- Update user passwords

---

## 🆘 Getting Help

### Check These First:
1. Application logs: `backend/app.log`
2. Browser console (F12 → Console tab)
3. Terminal output where backend is running

### Common URLs:
- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

### File Locations:
- Database: `backend/adinath.db`
- Logs: `backend/app.log`
- Backups: `backend/backups/`
- Config: `backend/app/main.py`

---

## ✅ Quick Start Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment exists (`backend/venv/`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database exists (`backend/adinath.db`)
- [ ] Admin user created (admin/admin123)
- [ ] Backend starts successfully (`start-backend.bat`)
- [ ] Can access http://localhost:8000
- [ ] Can login with admin credentials
- [ ] Can see 110 products in Products page
- [ ] CA Export works (test from API docs)

---

## 🎯 Next Steps After Setup

1. **Login** to the application
2. **Explore** the Products page (110 products loaded)
3. **Add farmers** to the system
4. **Create invoices** for testing
5. **Test CA Export** feature
6. **Customize** settings as needed
7. **Create production build** when ready

---

**Project Version:** 1.0.0  
**Last Updated:** November 14, 2026  
**Database:** SQLite with 110 products pre-loaded  
**Backend:** Python FastAPI  
**Frontend:** HTML/CSS/JavaScript  
**Desktop:** Electron wrapper
