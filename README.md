# 🛡️ VideoAI — AI/ML-Driven Video Analysis & Intelligence System

## Project Structure

```
AIML/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── database.py       # Neon DB (PostgreSQL) async connection
│   │   ├── api/v1/           # REST API routes
│   │   │   ├── auth.py       # Register / Login / JWT
│   │   │   ├── cameras.py    # Camera CRUD
│   │   │   ├── alerts.py     # Alert management
│   │   │   └── analytics.py  # Heatmap, timeline, overview
│   │   ├── models/           # SQLAlchemy ORM models
│   │   │   ├── camera.py
│   │   │   ├── alert.py
│   │   │   ├── detection.py
│   │   │   └── user.py
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic settings (reads .env)
│   │   │   └── security.py   # JWT + bcrypt
│   ├── migrations/           # Alembic DB migrations
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env.example          # ← Copy this to .env and fill in your Neon DB URL
│
├── ml-engine/                # Python ML processing engine
│   ├── main.py               # Entry point (CLI)
│   ├── detectors/
│   │   └── yolo_detector.py  # YOLOv8 object detection
│   ├── video/
│   │   └── capture.py        # VideoCapture (RTSP / file / webcam)
│   ├── weights/              # Place model .pt files here
│   └── requirements.txt
│
├── frontend/                 # Next.js dashboard (to be initialized)
└── shared/                   # Shared type definitions
```

---

## 🚀 Quick Start

### 1. Set up Neon DB
1. Go to [console.neon.tech](https://console.neon.tech) → Create project
2. Copy the **connection string** (it looks like: `postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/dbname`)

### 2. Configure Backend
```bash
cd backend
copy .env.example .env
# Edit .env — paste your Neon DB URL as DATABASE_URL (use postgresql+asyncpg:// prefix)
```

### 3. Install & Run Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** — you'll see the full Swagger UI.

### 4. Install & Run ML Engine
```bash
cd ml-engine
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Test on a local video file (no backend needed)
python main.py --source ./test.mp4 --camera-id YOUR_CAMERA_UUID --no-post

# Full run (posts detections to backend)
python main.py --source rtsp://YOUR_CAMERA_IP/stream --camera-id YOUR_CAMERA_UUID
```

### 5. Database Migrations (Alembic)
```bash
cd backend
# Create first migration
alembic revision --autogenerate -m "initial tables"
# Apply migration to Neon DB
alembic upgrade head
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon DB URL: `postgresql+asyncpg://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | JWT signing secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `FRONTEND_URL` | Next.js dev URL (default: `http://localhost:3000`) |
| `YOLO_MODEL_PATH` | Path to YOLOv8 weights file |
| `ML_CONFIDENCE_THRESHOLD` | YOLO confidence threshold (default: 0.5) |

---

## 📊 Implementation Status

The project is currently in **Phase 1 (Core Engine & File Analysis)**. The intelligent video analysis engine is functional and can process uploaded security footage to detect threats.

### ✅ What's Working Now
*   **Intelligent Analysis**: YOLOv8 integration for high-accuracy object detection.
*   **Security Alerts**: Automated logic to detect armed persons, weapons, and crowd surges.
*   **Multi-Format Support**: Processes `.mp4`, `.avi`, `.mkv`, and `.webm` files.
*   **Backend API**: Fast, asynchronous FastAPI server with auto-generated Swagger docs.
*   **Cloud Database**: Fully configured PostgreSQL (Neon DB) with SQLAlchemy models.

### 📡 Active API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System health check |
| POST | `/api/v1/video/analyze` | Upload video for AI threat analysis |

---

## 🚀 Development Roadmap

### 🔴 High Priority (Current Focus)
- [ ] **Live Stream Integration**: Support for RTSP/RTMP/HLS feeds from CCTV/Drones.
- [ ] **Database Persistence**: Saving all detected events and alerts to PostgreSQL.
- [ ] **Frontend Dashboard**: Real-time monitoring UI with Framer Motion animations.

### 🟡 Medium Priority
- [ ] **Behavioral Analysis**: Identifying loitering, falling, or restricted area intrusion.
- [ ] **WebSockets**: Real-time "Push" notifications for instant security alerts.
- [ ] **Visual Heatmaps**: Activity density maps for better intelligence gathering.

---

## 🛠️ Technology Stack
*   **Frontend**: React 19, Vite, Tailwind CSS 4, Framer Motion.
*   **Backend**: FastAPI, Python 3, SQLAlchemy, Uvicorn.
*   **AI/ML**: YOLOv8 (Ultralytics), OpenCV.
*   **Database**: PostgreSQL (Neon DB).

For more details, see [TECH_STACK.txt](./TECH_STACK.txt) and [PROJECT_STATUS.txt](./PROJECT_STATUS.txt).
