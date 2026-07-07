# 🎥 AI-CCTV — ระบบกล้องวงจรปิดอัจฉริยะ

> **Teg-CCTV v2.0** — ระบบจัดการกล้องวงจรปิดแบบ Real-time พร้อม AI สำหรับ **ตรวจจับ/จดจำใบหน้า (Face Recognition)** และ **อ่านป้ายทะเบียนรถ (License Plate Recognition — LPR)** ผ่าน RTSP Stream

---

## 📋 สารบัญ

- [ภาพรวมระบบ](#-ภาพรวมระบบ)
- [สถาปัตยกรรม (Architecture)](#-สถาปัตยกรรม-architecture)
- [Back-End](#-back-end)
- [UI (Front-End)](#-ui-front-end)
- [ฐานข้อมูล (Database)](#-ฐานข้อมูล-database)
- [การติดตั้งและเริ่มต้นใช้งาน](#-การติดตั้งและเริ่มตนใชงาน)
- [โครงสร้างโปรเจกต์](#-โครงสรางโปรเจกต)

---

## 🌐 ภาพรวมระบบ

AI-CCTV เป็นระบบที่รวม **Server (Back-End)** และ **Desktop Application (UI)** เข้าด้วยกัน โดยมีความสามารถหลักดังนี้:

| ความสามารถ | รายละเอียด |
|---|---|
| 🎥 **Live Streaming** | รับ RTSP Stream จากกล้อง IP Camera แล้วส่งต่อเป็น MJPG ผ่าน WebSocket |
| 👤 **Face Recognition** | ตรวจจับและจดจำใบหน้าพนักงาน โดยใช้ InsightFace (buffalo_l) + ONNX Runtime |
| 🚗 **License Plate Recognition** | ตรวจจับป้ายทะเบียนรถด้วย YOLOv8 + Tesseract OCR |
| 📹 **Video Recording** | บันทึกวิดีโอต่อเนื่องเป็น Segment (FFmpeg / HEVC) |
| 📊 **Reports** | ดูรายงานการเข้า-ออกของใบหน้าและทะเบียนรถ พร้อม Export CSV |
| 🔐 **Authentication** | ระบบ Login ด้วย JWT Token + bcrypt Password Hashing + Session Management |
| 👥 **Employee Management** | ลงทะเบียนพนักงาน พร้อม Face Embedding สูงสุด 5 มุม (center/left/right) |
| ⚙️ **Admin Tools** | จัดการผู้ใช้, กล้อง, แผนก, รีเซ็ตรหัสผ่าน, ดู Event Log |

---

## 🏗 สถาปัตยกรรม (Architecture)

```
┌──────────────────────────────────────────────────────────┐
│                    IP Cameras (RTSP)                      │
│              Hikvision / Dahua / ONVIF etc.               │
└──────────────┬───────────────┬────────────────────────────┘
               │ RTSP Stream   │ RTSP Sub-stream
               ▼               ▼
┌──────────────────────────────────────────────────────────┐
│                 Back-End Server (FastAPI)                 │
│  ┌────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │   Face      │  │   Car Plate    │  │   Video       │  │
│  │   Worker    │  │   Worker       │  │   Recorder    │  │
│  │ (InsightFace│  │ (YOLO+Tesseract│  │ (FFmpeg/HEVC) │  │
│  │  buffalo_l) │  │  OCR)          │  │               │  │
│  └──────┬─────┘  └──────┬─────────┘  └──────┬────────┘  │
│         │               │                    │           │
│  ┌──────▼───────────────▼────────────────────▼────────┐  │
│  │              PostgreSQL Database                    │  │
│  │  (face_embeddings, car_log, face_detection_details) │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │           REST API + WebSocket Endpoints            │  │
│  │  /auth  /cameras  /employees  /recordings  /reports │  │
│  │  /ws/mjpg/{camera}   /ws/ui-updates                 │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────────────────┘
               │ HTTP REST + WebSocket (MJPG)
               ▼
┌──────────────────────────────────────────────────────────┐
│               UI Desktop Application (PyQt5)             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Login    │  │  Camera  │  │ Employee │  │ Admin   │ │
│  │  Dialog   │  │  Grid    │  │ Mgmt     │  │ Hub     │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## ⚙️ Back-End

### ภาพรวม

Back-End เป็น **REST API Server** ที่พัฒนาด้วย **FastAPI** ทำหน้าที่เป็นศูนย์กลางประมวลผล AI ทั้งหมด รวมถึงจัดการ RTSP Stream, บันทึกวิดีโอ, และเชื่อมต่อฐานข้อมูล

**ตำแหน่งไฟล์:** `AI-CCTV_backEnd/`

### เครื่องมือและ Libraries ที่ใช้

| เครื่องมือ | เวอร์ชัน | หน้าที่ |
|---|---|---|
| **FastAPI** | 0.110.0 | Web framework สำหรับสร้าง REST API + WebSocket |
| **Uvicorn** | 0.29.0 | ASGI Server สำหรับ run FastAPI |
| **PostgreSQL** | — | ฐานข้อมูลหลักเก็บข้อมูลทั้งหมด |
| **psycopg2** | — | Python driver สำหรับเชื่อมต่อ PostgreSQL |
| **InsightFace** | 0.7.3 | AI Model สำหรับตรวจจับและจดจำใบหน้า (ใช้โมเดล `buffalo_l`) |
| **ONNX Runtime** | 1.17.3 | Runtime สำหรับ run AI model (รองรับ CPU/GPU) |
| **Ultralytics (YOLOv8)** | 8.3.0 | ตรวจจับป้ายทะเบียนรถจากภาพ (Object Detection) |
| **EasyOCR** | 1.7.1 | อ่านตัวอักษรจากป้ายทะเบียน (Optical Character Recognition) |
| **Tesseract OCR** | 5.5.0 | OCR Engine ตัวหลักสำหรับอ่านป้ายทะเบียนรถไทย |
| **OpenCV** | 4.10.0 | ประมวลผลภาพ, จับ RTSP Stream, resize, crop ภาพ |
| **FFmpeg** | — | Encoding/Recording วิดีโอ (HEVC/H.265 ผ่าน `hevc_nvenc` หรือ `libx265`) |
| **PyJWT** | — | สร้างและตรวจสอบ JSON Web Token (JWT) |
| **bcrypt** | — | Hash รหัสผ่านผู้ใช้อย่างปลอดภัย |
| **NumPy** | 1.26.4 | คำนวณ Embedding, L2 Normalization, Cosine Similarity |
| **Pillow** | 10.3.0 | วาดข้อความภาษาไทยบน Overlay (ใช้ฟอนต์ `.ttf`) |
| **PyTorch** | — | Backend สำหรับ YOLOv8 (Ultralytics) |

### โครงสร้างไฟล์ Back-End

```
AI-CCTV_backEnd/
├── server.py                     # 🚀 Entry point — สร้าง FastAPI app + lifespan
├── server_settings.json          # ⚙️ Runtime settings (e.g., SEGMENT_MINUTES)
├── requirements.txt              # 📦 Python dependencies
├── Car_Plate_True.pt             # 🤖 YOLOv8 model สำหรับตรวจจับป้ายทะเบียน
├── angsa.ttf                     # 🔤 Thai font สำหรับวาด Overlay ภาษาไทย
├── Database.sql                  # 🗄️ SQL schema สำหรับสร้างฐานข้อมูล
│
├── service/                      # ── Business Logic Layer ──
│   ├── config.py                 # ค่าตั้งต้นทุกอย่าง (ENV, paths, JWT, RTSP, InsightFace)
│   ├── app_state.py              # Shared mutable state (frames, workers, subscribers)
│   ├── auth.py                   # JWT token creation/verification + session management
│   ├── database.py               # PostgreSQL wrapper (CRUD ทุกตาราง)
│   ├── face_insight.py           # InsightFace model setup + face utility helpers
│   ├── face_camera_worker.py     # Worker thread: ตรวจจับ/จดจำใบหน้า real-time
│   ├── car_camera_worker.py      # Worker thread: ตรวจจับป้ายทะเบียน + OCR real-time
│   ├── camera_manager.py         # จัดการ spawn/stop กล้อง, health monitor, frame encoding
│   ├── record.py                 # VideoRecorder: บันทึกวิดีโอเป็น segment (FFmpeg pipe)
│   └── utils.py                  # Utilities: RTSP env, frame hash, image processing
│
├── routers/                      # ── API Routes Layer ──
│   ├── auth_routes.py            # POST /auth/login, /auth/logout, /auth/change-password
│   ├── camera_routes.py          # CRUD /cameras + start/stop/preview control
│   ├── employee_routes.py        # CRUD /employees + face enrollment
│   ├── user_routes.py            # User profile & management
│   ├── recording_routes.py       # GET /recordings + file streaming
│   ├── report_routes.py          # GET /reports (face & car logs, CSV export)
│   ├── streaming_routes.py       # WebSocket /ws/mjpg/{camera} + /ws/ui-updates
│   └── admin_routes.py          # Admin-only endpoints
│
├── recordings/                   # 📁 โฟลเดอร์เก็บไฟล์วิดีโอที่บันทึก
├── face_crops/                   # 📁 โฟลเดอร์เก็บภาพ face crop
└── output/                       # 📁 โฟลเดอร์ output ทั่วไป
```

### การทำงานของ Back-End (Workflow)

#### 1. Startup (Lifespan)

เมื่อ Server เริ่มทำงาน (`server.py`):

1. **เชื่อมต่อ Database** — สร้าง instance `Database()` เชื่อมต่อ PostgreSQL
2. **โหลด Settings** — อ่านค่า `server_settings.json` (เช่น ความยาว segment วิดีโอ)
3. **Spawn กล้อง** — ดึงรายชื่อกล้องจาก DB แล้ว spawn Worker Thread สำหรับแต่ละกล้อง
4. **เริ่ม Health Monitor** — Thread ที่ตรวจสอบสถานะกล้องทุก 10 วินาที

#### 2. Face Recognition Pipeline (`face_camera_worker.py`)

```
RTSP Frame → InsightFace Detection → Face Crop
    → Embedding Extraction (512-dim vector)
    → L2 Normalize → Cosine Similarity matching
    → ถ้า similarity ≥ threshold → ระบุตัวตนสำเร็จ
    → บันทึกลง face_detection_details table
    → วาด Overlay (ชื่อ, แผนก, confidence) บน Frame
```

- ใช้ **InsightFace `buffalo_l`** model (ผ่าน ONNX Runtime)
- รองรับทั้ง **CPU** และ **CUDA GPU**
- ระบบ **Dual Face App**: แยก Runtime (1280×1280) กับ Enrollment (512×512)
- เก็บ Embedding ได้สูงสุด **5 ช่อง** ต่อพนักงาน (multi-angle: center, left, right)
- ตรวจสอบคุณภาพภาพก่อน Enrollment (ขนาดหน้า ≥ 140px, blur variance ≥ 120, det_score ≥ 0.60)

#### 3. License Plate Recognition Pipeline (`car_camera_worker.py`)

```
RTSP Frame → CLAHE Enhancement + Sharpen
    → YOLOv8 Detection (Car_Plate_True.pt)
    → Crop ป้ายทะเบียน + Quality Check (sharp, min size)
    → Tesseract OCR (ภาษาไทย + อังกฤษ)
    → Normalize ป้ายทะเบียน (เลขไทย→อารบิก, ลบ space)
    → ตรวจสอบ Whitelist ใน DB
    → บันทึกลง car_log table
```

- ใช้ **Custom YOLOv8 model** (`Car_Plate_True.pt`) สำหรับ detect ป้ายทะเบียน
- Pre-processing ด้วย **CLAHE** (Contrast Limited Adaptive Histogram Equalization) + **Sharpening**
- OCR ด้วย **Tesseract** (รองรับภาษาไทย-อังกฤษ)
- มี **Cooldown** (OCR_MIN_INTERVAL = 180 วินาที) ป้องกัน OCR ซ้ำ
- ใช้ **ThreadPoolExecutor** สำหรับ OCR worker แบบ parallel

#### 4. Video Recording (`record.py`)

- บันทึกวิดีโอผ่าน **FFmpeg subprocess pipe**
- Codec: `hevc_nvenc` (GPU) หรือ `libx265` (CPU fallback)
- ตั้งค่า Resolution 1920×1080, FPS 25, Bitrate 6000k
- แบ่งเป็น **Segment** ตามเวลาที่กำหนด (default 3 นาที)
- รองรับ **Letterbox** เพื่อคงสัดส่วนภาพ
- ใช้ `.part` file เพื่อป้องกันไฟล์เสียหายระหว่างบันทึก

#### 5. WebSocket Streaming

- **`/ws/mjpg/{camera_name}`** — ส่ง MJPG frame ผ่าน WebSocket (15 FPS)
- **`/ws/ui-updates`** — Push event updates ไปยัง UI (เช่น กล้อง online/offline)
- รองรับ **Dual stream**: Main stream (ประมวลผล AI) + Sub stream (preview ลด bandwidth)

#### 6. Authentication & Authorization

- **JWT Token** (HS256) — expire ได้ (default 120 นาที)
- **bcrypt** — hash password ก่อนเก็บใน DB
- **Session Management** — Single session per user (force login kick ผู้ใช้เก่า)
- **Role-based Access** — แบ่ง Admin / User ธรรมดา + กำหนด department access
- **Token Claims**: sub, department, access[], is_admin, sid, jti

---

## 🖥 UI (Front-End)

### ภาพรวม

UI เป็น **Desktop Application** พัฒนาด้วย **PyQt5** ออกแบบเป็น Premium Monochrome Theme (White/Gray/Black) พร้อม animations และ shadow effects สื่อสารกับ Back-End ผ่าน REST API + WebSocket

**ตำแหน่งไฟล์:** `UI/`

### เครื่องมือและ Libraries ที่ใช้

| เครื่องมือ | หน้าที่ |
|---|---|
| **PyQt5** | GUI Framework หลัก (Widgets, Layouts, Signals/Slots, Multimedia) |
| **QMediaPlayer + QVideoWidget** | เล่นวิดีโอ Recording (YouTube-like Player) |
| **WebSocket (websockets)** | รับ MJPG Stream จาก Server แบบ real-time |
| **requests** | เรียก REST API (Login, CRUD cameras, employees, reports) |
| **OpenCV** | แปลง/ประมวลผลภาพ Frame ที่ได้จาก WebSocket |
| **NumPy** | จัดการ Array ของ Frame |
| **pytz** | แปลง Timezone เป็น Asia/Bangkok |

### โครงสร้างไฟล์ UI

```
UI/
├── app_main.py              # 🚀 Entry point — Splash Screen → Main Window
├── config.py                # ⚙️ Shared config, imports, constants (SERVER_BASE, paths)
├── theme.py                 # 🎨 Premium Monochrome Design System (Colors, Stylesheets, Animations)
├── main_window.py           # 🪟 Main Window: Toolbar + Camera Grid + Sidebar
├── api_client.py            # 🌐 APIClient (REST) + MJPGWebSocketPlayer (WebSocket)
├── components.py            # 🧩 Reusable components: YouTubeLikePlayer, CameraStreamTile, SplashScreen
├── auth_dialogs.py          # 🔐 Login, Change Password, Register, Temp Password dialogs
├── camera_dialogs.py        # 📷 Add, Edit, Delete, Select Camera dialogs
├── employee_dialogs.py      # 👤 Add, Delete, Edit Employee dialogs
├── admin_dialogs.py         # ⚙️ Admin Hub, Reports, Recordings, Camera Event Log
├── utils.py                 # 🔧 Utility functions (RTSP URL builder, parsers)
│
└── Main/
    ├── UI_Main.py           # 📦 Legacy monolithic UI (ก่อนแยกไฟล์) — สำรอง
    └── assets/              # 🖼️ ไฟล์ภาพ, ไอคอน, โลโก้
```

### การทำงานของ UI (Workflow)

#### 1. เริ่มต้นแอปพลิเคชัน (`app_main.py`)

```
เปิดแอป → แสดง Splash Screen (2.2 วินาที)
    → สร้าง Main Window (DeepBlueGridUltimate)
    → แสดง Login Dialog
    → Login สำเร็จ → โหลดรายชื่อกล้อง → แสดง Camera Grid
```

- ตั้งค่า **High DPI Scaling** สำหรับจอ 4K
- โหลด **App Icon** จาก `assets/logo.png`
- ใช้ฟอนต์ **Segoe UI**

#### 2. ระบบ Login (`auth_dialogs.py`)

- **DeepBlueLoginDialog** — หน้าจอ Login แบบ Glassmorphism Card
- รองรับ **Remember Me** (บันทึก token ลง `config.json`)
- ถ้ามี Session ค้างอยู่ สามารถ **Force Login** เพื่อ kick session เก่าได้
- **RegisterDialog** — สร้างบัญชีผู้ใช้ใหม่ (Admin only)
- **ResetTempPasswordDialog** — รีเซ็ตรหัสผ่านชั่วคราว (Admin only)

#### 3. Camera Grid (`main_window.py` + `components.py`)

- แสดงกล้องแบบ **Grid Layout** (สูงสุด 9 กล้อง)
- แต่ละช่อง = **CameraStreamTile** ที่รับ MJPG Stream ผ่าน WebSocket
- **Double-click** กล้องเพื่อขยายเต็มจอ (Maximize/Restore)
- **Sidebar ซ้าย** — แสดงรายชื่อกล้องพร้อม Status Icon (🟢 Online / 🔴 Offline / ⚪ Unknown)
- **Toolbar** — ปุ่ม Refresh, Reports, Recordings, Logout

#### 4. WebSocket MJPG Player (`api_client.py`)

```
เชื่อมต่อ ws://server:8000/ws/mjpg/{camera_name}
    → รับ Binary JPEG data
    → แปลงเป็น QPixmap
    → แสดงผลบน QLabel (CameraStreamTile)
    → วน loop ต่อเนื่อง (real-time)
```

- ใช้ **asyncio + websockets** library
- ทำงานใน **Background Thread** เพื่อไม่ block UI
- มี **Auto-reconnect** เมื่อ connection หลุด

#### 5. จัดการพนักงาน (`employee_dialogs.py`)

- **AddEmployeeDialog** — ลงทะเบียนพนักงานใหม่ พร้อมอัพโหลดรูปใบหน้า
- รองรับเลือก **มุมใบหน้า** (Center / Left / Right)
- แสดง Preview ก่อนอัพโหลด + Resize เป็น 200×200
- **EditEmployeeDialog** — แก้ไขข้อมูลพนักงาน
- **DeleteEmployeeDialog** — ลบพนักงานออกจากระบบ

#### 6. จัดการกล้อง (`camera_dialogs.py`)

- **AddCameraDialog** — เพิ่มกล้องใหม่ (กรอก Name, RTSP URL, Zone, Company)
- รองรับหลายยี่ห้อกล้อง: **Hikvision, Dahua, ONVIF** พร้อมสร้าง URL อัตโนมัติ
- **EditCameraDialog** — แก้ไข URL / Zone / Company
- **SelectCameraDialog** — เลือกกล้องที่จะแสดงใน Grid

#### 7. Admin Hub (`admin_dialogs.py`)

- **AdminHub** — Dashboard สำหรับ Admin แบบ Card Grid
- **Reports Dialog** — ดูรายงานการตรวจจับใบหน้า/ทะเบียนรถ ตามช่วงวันที่
- **Recordings Dialog** — ดูรายการวิดีโอที่บันทึก พร้อม **YouTube-like Player** (Play, Pause, Seek, Timeline)
- **Camera Event Log** — ดู Event Log สถานะกล้อง (OK/DOWN) ย้อนหลัง

#### 8. ระบบ Theme (`theme.py`)

- **Premium Monochrome Design** — โทนสี White/Gray/Black
- **Colors class** — Palette กลาง (BG_DARKEST `#111111`, BG_DARK `#1a1a1a`, BG_CARD `#222222` ...)
- **QGraphicsDropShadowEffect** — เงาตกสำหรับ Card/Dialog
- **QPropertyAnimation** — Animations สำหรับ fade-in, slide, resize
- **Global Stylesheet** — CSS-like stylesheet สำหรับ Widget ทุกตัว (QPushButton, QLineEdit, QComboBox, QScrollBar ...)
- **Semantic Colors** — Success (🟢), Warning (🟡), Danger (🔴)

### Design System ของ UI

```
Color Palette:
┌─────────────────────────────────────────────┐
│  BG_DARKEST  #111111  ██████████████████    │
│  BG_DARK     #1a1a1a  ██████████████████    │
│  BG_CARD     #222222  ██████████████████    │
│  BG_ELEVATED #2c2c2c  ██████████████████    │
│  BORDER      #333333  ██████████████████    │
│  TEXT_PRIMARY #f0f0f0  ██████████████████    │
│  TEXT_SECONDARY #999999 ████████████████    │
│  SUCCESS     #4caf50  ██████████████████    │
│  DANGER      #f44336  ██████████████████    │
└─────────────────────────────────────────────┘
```

---

## 🗄 ฐานข้อมูล (Database)

### ระบบจัดการฐานข้อมูล

- **PostgreSQL** — ฐานข้อมูลหลัก
- เชื่อมต่อผ่าน **psycopg2** driver
- รองรับ **DATABASE_URL** หรือ แยกค่า `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### ตารางหลัก

| ตาราง | หน้าที่ |
|---|---|
| `login` | เก็บข้อมูลผู้ใช้ (username, password hash, department, access, is_admin) |
| `cameras` | เก็บข้อมูลกล้อง (camera_name, RTSP URL, zone, company) |
| `face_embeddings` | เก็บ Face Embedding 5 ช่อง + รูปภาพ + ข้อมูลพนักงาน |
| `face_detection_details` | Log การตรวจจับใบหน้า (camera, name, dept, confidence, similarity, bbox, timestamp) |
| `car_log` | Log การตรวจจับป้ายทะเบียน (plate_number, province, camera, status, direction) |
| `whitelist_car` | รายชื่อรถที่อนุญาต (license, province) |
| `camera_status_events` | Log สถานะกล้อง (event_time, camera_name, status: OK/DOWN) |
| `error_log` | Log ข้อผิดพลาดของระบบ |

---

## 🚀 การติดตั้งและเริ่มต้นใช้งาน

### ข้อกำหนดเบื้องต้น (Prerequisites)

- **Python** 3.10+
- **PostgreSQL** 12+
- **Tesseract OCR** 5.x (ติดตั้งแยก + ตั้ง PATH)
- **FFmpeg** (สำหรับ Video Recording)
- **CUDA Toolkit** (optional, สำหรับ GPU acceleration)

### ติดตั้ง Back-End

```bash
# 1. เข้าไปที่โฟลเดอร์ Back-End
cd AI-CCTV_backEnd

# 2. สร้าง Virtual Environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. ติดตั้ง Dependencies
pip install -r requirements.txt

# 4. ตั้งค่า Environment Variables (สร้างไฟล์ .env)
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=your_db_name
# DB_USER=postgres
# DB_PASSWORD=your_password
# JWT_SECRET=your-secret-key
# TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe

# 5. สร้างฐานข้อมูล
psql -U postgres -f Database.sql

# 6. รัน Server
python server.py
# Server จะรันที่ http://0.0.0.0:8000
```

### ติดตั้ง UI

```bash
# 1. เข้าไปที่โฟลเดอร์ UI
cd UI

# 2. ติดตั้ง Dependencies (ถ้ายังไม่ได้ติดตั้ง)
pip install PyQt5 requests websockets opencv-python numpy pytz

# 3. ตั้งค่า Server URL (แก้ไขใน config.py หรือตั้ง ENV)
# set SERVER_BASE=http://192.168.1.104:8000

# 4. ใส่โลโก้ที่ UI/assets/logo.png

# 5. รัน UI
python app_main.py
```

### Environment Variables สำคัญ

| ตัวแปร | ค่าเริ่มต้น | คำอธิบาย |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `postgres` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | — | Database password |
| `JWT_SECRET` | `change-me` | Secret key สำหรับ sign JWT |
| `JWT_EXPIRE_MINUTES` | `120` | อายุ token (นาที) |
| `TESSERACT_PATH` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | Path ไปยัง Tesseract executable |
| `RECORD_ROOT` | `./recordings` | โฟลเดอร์เก็บวิดีโอ |
| `RECORD_CODEC` | `hevc_nvenc` | Video codec (hevc_nvenc, libx265, hevc_qsv) |
| `SEGMENT_MINUTES` | `15` | ความยาว segment วิดีโอ (นาที) |
| `FACE_MODEL_NAME` | `buffalo_l` | InsightFace model name |
| `SERVER_BASE` | `http://192.168.1.104:8000` | URL ของ Back-End Server (สำหรับ UI) |

---

## 📁 โครงสร้างโปรเจกต์

```
AI_CCTV/
├── README.md                          # 📖 ไฟล์นี้
│
├── AI-CCTV_backEnd/                   # ⚙️ Back-End Server
│   ├── server.py                      #     Entry point (FastAPI)
│   ├── requirements.txt               #     Python dependencies
│   ├── server_settings.json           #     Runtime settings
│   ├── Car_Plate_True.pt              #     YOLO model (ป้ายทะเบียน)
│   ├── angsa.ttf                      #     Thai font
│   ├── Database.sql                   #     SQL schema
│   ├── service/                       #     Business logic layer
│   │   ├── config.py                  #       Configuration
│   │   ├── app_state.py               #       Shared state
│   │   ├── auth.py                    #       JWT + auth
│   │   ├── database.py                #       PostgreSQL wrapper
│   │   ├── face_insight.py            #       InsightFace helpers
│   │   ├── face_camera_worker.py      #       Face recognition worker
│   │   ├── car_camera_worker.py       #       License plate worker
│   │   ├── camera_manager.py          #       Camera lifecycle
│   │   ├── record.py                  #       Video recording (FFmpeg)
│   │   └── utils.py                   #       Utilities
│   └── routers/                       #     API routes
│       ├── auth_routes.py             #       Authentication
│       ├── camera_routes.py           #       Camera management
│       ├── employee_routes.py         #       Employee management
│       ├── user_routes.py             #       User management
│       ├── recording_routes.py        #       Recording access
│       ├── report_routes.py           #       Reports & analytics
│       ├── streaming_routes.py        #       WebSocket streaming
│       └── admin_routes.py            #       Admin endpoints
│
└── UI/                                # 🖥️ Desktop Application
    ├── app_main.py                    #     Entry point (PyQt5)
    ├── config.py                      #     Shared config
    ├── theme.py                       #     Design system
    ├── main_window.py                 #     Main window
    ├── api_client.py                  #     API & WebSocket client
    ├── components.py                  #     Reusable widgets
    ├── auth_dialogs.py                #     Login/Register dialogs
    ├── camera_dialogs.py              #     Camera management dialogs
    ├── employee_dialogs.py            #     Employee management dialogs
    ├── admin_dialogs.py               #     Admin tools & reports
    ├── utils.py                       #     Utility functions
    └── Main/
        ├── UI_Main.py                 #     Legacy monolithic UI
        └── assets/                    #     Images, icons, logo
```

---

## 📄 เอกสารเพิ่มเติม

- `AI-CCTV_backEnd/ขั้นตอนการติดตั้ง SERVER.pdf` — คู่มือติดตั้ง Server
- `AI-CCTV_backEnd/คู่มือการใช้งาน โปรแกรม.pdf` — คู่มือการใช้งานโปรแกรม
- `UI/function_description.md` — รายละเอียดฟังก์ชันทั้งหมดของ UI

---

<p align="center">
  <b>Teg-CCTV v2.0</b> — AI-Powered Surveillance Management System<br>
  Built with ❤️ using FastAPI + PyQt5 + InsightFace + YOLOv8
</p>
