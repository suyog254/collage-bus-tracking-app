# 🚌 BusTracker — CDIPS College Bus Tracking System

> **A real-time GPS bus tracking system for CDIPS College, Indore (M.P.)**  
> Built with Flask · SQLite · Leaflet Maps · Chart.js

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Installation & Setup](#-installation--setup)
- [Requirements](#-requirements)
- [Default Login Credentials](#-default-login-credentials)
- [API Endpoints](#-api-endpoints)
- [Pages & Screens](#-pages--screens)
- [CSV Backup System](#-csv-backup-system)
- [Security Notes](#-security-notes-for-production)
- [Author](#-author)

---

## 📌 Project Overview

**BusTracker** is a full-stack web application developed for **CDIPS College, Indore** to manage and track college buses in real-time. The system provides dedicated dashboards for **students**, **drivers**, and **administrators** — featuring live GPS tracking, gate entry/exit logging, push notifications, and analytics reports.

---

## ✨ Features

### 🎓 Student Panel
- Live bus location displayed on an interactive map (Leaflet.js)
- Estimated Time of Arrival (ETA) at the student's assigned stop
- View assigned route, bus number, and driver contact details
- Bell notification system with unread count, mark-as-read, and delete options
- Ability to switch between available routes

### ⚙️ Admin Panel
- Full CRUD operations for Buses, Routes, and Students
- Bus activation and deactivation with alternate bus reassignment
- Deactivation reason selection: Technical Issue, Accident, Maintenance, or Other
- Automatic student notifications upon bus deactivation
- Gate entry/exit log management with delete support
- Reports and analytics powered by Chart.js (Bar, Pie, Horizontal Bar charts)
- CSV export for gate logs and driver data backup
- Route reset functionality to restore original bus assignments

### 📡 Driver GPS Panel
- Real-time GPS sharing directly from the driver's mobile browser
- GPS On/Off toggle for each bus
- Live location pushed to the student map at regular intervals
- Displays speed and GPS accuracy

### 🔒 Gate Log System
- Log bus entries and exits at the college gate
- Filter logs by date range, bus number, and entry type
- Export filtered gate logs as a downloadable CSV file

---

## 🛠 Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python 3.x, Flask                   |
| Database     | SQLite3 (`bus_tracker.db`)          |
| Frontend     | HTML5, CSS3, Jinja2 Templates       |
| Maps         | Leaflet.js / Google Maps API        |
| Charts       | Chart.js 4.4.1                      |
| Timezone     | `pytz` (IST — Asia/Kolkata)         |
| Styling      | Custom CSS (`style.css`)            |
| Auth         | Flask Session (cookie-based)        |
| CSV Export   | Python `csv` module + `io.StringIO` |

---

## 📁 Project Structure

```
BusTracker/
│
├── app.py                       # Main Flask application (all routes & logic)
├── bus_tracker.db               # SQLite database (auto-created on first run)
│
├── templates/
│   ├── base.html                # Base layout: navbar, flash messages, footer
│   ├── home.html                # Public landing page with features & stats
│   ├── register.html            # Student registration with live validation
│   ├── student_login.html       # Student login page
│   ├── admin_login.html         # Admin login page
│   ├── dashboard.html           # Student dashboard with live map & route info
│   ├── driver_gps.html          # Driver GPS sharing panel
│   ├── admin.html               # Admin dashboard (Buses, Routes, Students, Logs tabs)
│   ├── deactivate_confirm.html  # Bus deactivation confirmation with alternate bus picker
│   ├── students.html            # Full student list with search, filter & notifications
│   ├── gate_logs.html           # Complete gate logs listing page
│   ├── routes.html              # Public routes listing page
│   └── reports.html             # Analytics, charts, and CSV export
│
├── static/
│   └── css/
│       └── style.css            # Main stylesheet
│
├── backup_buses.csv             # Auto-generated bus data backup
├── backup_routes.csv            # Auto-generated routes backup
├── backup_users.csv             # Auto-generated student data backup
└── backup_gate_logs.csv         # Auto-generated gate log backup
```

---

## 🗄 Database Schema

### `users`
| Column     | Type      | Description                                         |
|------------|-----------|-----------------------------------------------------|
| id         | INTEGER   | Primary key (auto-increment)                        |
| name       | TEXT      | Full name of the user                               |
| email      | TEXT      | Unique email used as login credential               |
| password   | TEXT      | Password (plain text — use hashing for production)  |
| role       | TEXT      | `admin` or `student`                                |
| phone      | TEXT      | 10-digit mobile number                              |
| route_id   | INTEGER   | Foreign key → routes.id                             |
| created_at | TIMESTAMP | Registration timestamp                              |

### `buses`
| Column         | Type    | Description                          |
|----------------|---------|--------------------------------------|
| id             | INTEGER | Primary key (auto-increment)         |
| bus_number     | TEXT    | Unique bus identifier (e.g. BUS-01)  |
| driver_name    | TEXT    | Driver's full name                   |
| driver_phone   | TEXT    | Driver's contact number              |
| driver_address | TEXT    | Driver's residential address         |
| capacity       | INTEGER | Seat capacity (default: 40)          |
| status         | TEXT    | `active` or `inactive`               |
| current_lat    | REAL    | Last known latitude                  |
| current_lng    | REAL    | Last known longitude                 |

### `routes`
| Column          | Type    | Description                              |
|-----------------|---------|------------------------------------------|
| id              | INTEGER | Primary key (auto-increment)             |
| route_name      | TEXT    | Display name of the route                |
| bus_id          | INTEGER | Foreign key → buses.id (current bus)     |
| original_bus_id | INTEGER | Original bus assignment (used for reset) |
| start_point     | TEXT    | First stop on the route                  |
| end_point       | TEXT    | Last stop on the route                   |
| departure_time  | TEXT    | Departure time in HH:MM format           |
| arrival_time    | TEXT    | Arrival time in HH:MM format             |
| stops           | TEXT    | All stops as a string (arrow-delimited)  |

### `gate_logs`
| Column     | Type      | Description                            |
|------------|-----------|----------------------------------------|
| id         | INTEGER   | Primary key (auto-increment)           |
| bus_id     | INTEGER   | Foreign key → buses.id                 |
| bus_number | TEXT      | Denormalized bus number for display    |
| entry_type | TEXT      | `Entry` or `Exit`                      |
| log_time   | TIMESTAMP | Auto-generated timestamp               |
| noted_by   | TEXT      | Who logged the entry (default: System) |

### `notifications`
| Column     | Type      | Description                     |
|------------|-----------|---------------------------------|
| id         | INTEGER   | Primary key (auto-increment)    |
| user_id    | INTEGER   | Foreign key → users.id          |
| message    | TEXT      | Notification message content    |
| is_read    | INTEGER   | 0 = unread, 1 = read            |
| created_at | TIMESTAMP | Auto-generated timestamp        |

### `bus_live_location`
| Column     | Type    | Description                              |
|------------|---------|------------------------------------------|
| id         | INTEGER | Primary key (auto-increment)             |
| bus_id     | INTEGER | Foreign key → buses.id (unique per bus)  |
| lat        | REAL    | Current latitude coordinate              |
| lng        | REAL    | Current longitude coordinate             |
| accuracy   | REAL    | GPS accuracy in meters                   |
| speed      | TEXT    | Current speed from browser GPS API       |
| gps_active | INTEGER | 0 = offline, 1 = broadcasting live       |
| updated_at | TEXT    | Timestamp of the last GPS update         |

---

## ⚙️ Installation & Setup

### Step 1 — Clone the Repository
```bash
git clone https://github.com/your-username/bustracker-cdips.git
cd bustracker-cdips
```

### Step 2 — Create a Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Run the Application
```bash
python app.py
```

The application will start at: **http://127.0.0.1:5000**

> The database (`bus_tracker.db`) is created automatically on the first run, along with default seed data: 3 buses, 3 routes, and 1 admin account.

---

## 📦 Requirements

Create a `requirements.txt` file in the project root with the following:

```
Flask==3.0.3
pytz==2024.1
```

Or install manually:
```bash
pip install Flask pytz
```

> **Python Version:** 3.8 or higher is recommended.  
> All other libraries used (`sqlite3`, `csv`, `io`, `re`, `functools`, `datetime`) are part of Python's standard library and require no additional installation.

---

## 🔑 Default Login Credentials

| Role    | Email              | Password     |
|---------|--------------------|--------------|
| Admin   | admin@cdips.edu    | admin123     |
| Student | *(register first)* | *(your own)* |

> ⚠️ **Important:** Passwords are currently stored as plain text. Before deploying to production, switch to hashed passwords using `werkzeug.security`.

---

## 🌐 API Endpoints

| Method   | Endpoint                          | Auth    | Description                          |
|----------|-----------------------------------|---------|--------------------------------------|
| GET      | `/`                               | Public  | Home / landing page                  |
| GET      | `/routes-info`                    | Public  | All routes listing                   |
| GET/POST | `/register`                       | Public  | Student registration                 |
| GET/POST | `/student/login`                  | Public  | Student login                        |
| GET/POST | `/admin/login`                    | Public  | Admin login                          |
| GET      | `/logout/student`                 | Student | Student logout                       |
| GET      | `/logout/admin`                   | Admin   | Admin logout                         |
| GET      | `/dashboard`                      | Student | Student dashboard with live map      |
| GET      | `/admin`                          | Admin   | Admin dashboard                      |
| POST     | `/admin/add-bus`                  | Admin   | Add a new bus                        |
| GET      | `/admin/delete-bus/<id>`          | Admin   | Delete a bus                         |
| GET/POST | `/admin/bus-status/<id>/<status>` | Admin   | Activate or deactivate a bus         |
| POST     | `/admin/add-route`                | Admin   | Add a new route                      |
| GET      | `/admin/delete-route/<id>`        | Admin   | Delete a route                       |
| GET      | `/admin/fix-routes`               | Admin   | Reset routes to original buses       |
| POST     | `/admin/add-gate-log`             | Admin   | Add a gate log entry                 |
| GET      | `/admin/delete-gate-log/<id>`     | Admin   | Delete a gate log entry              |
| GET      | `/admin/students`                 | Admin   | Student list with search and filter  |
| GET      | `/admin/delete-student/<id>`      | Admin   | Remove a student                     |
| GET      | `/admin/gate-logs`                | Admin   | Full gate logs page                  |
| GET      | `/admin/reports`                  | Admin   | Analytics and reports page           |
| GET      | `/admin/reports/export`           | Admin   | Export filtered gate logs as CSV     |
| GET      | `/admin/reports/export-drivers`   | Admin   | Export driver data backup as CSV     |
| GET      | `/driver/gps/<bus_id>`            | Admin   | Driver GPS sharing panel             |
| POST     | `/api/gps_toggle`                 | Admin   | Toggle GPS on/off for a bus          |
| POST     | `/api/update_gps`                 | Admin   | Receive GPS coordinates from driver  |
| GET      | `/api/live_location/<bus_id>`     | Public  | Get live location of a specific bus  |
| GET      | `/api/all_gps_status`             | Admin   | Live GPS status of all active buses  |
| POST     | `/mark-notifications-read`        | Student | Mark all notifications as read       |
| POST     | `/delete-all-notifications`       | Student | Delete all notifications             |
| POST     | `/delete-notification/<id>`       | Student | Delete a single notification         |

---

## 📄 Pages & Screens

| Page                      | Template File              | Access  |
|---------------------------|----------------------------|---------|
| Home / Landing Page       | `home.html`                | Public  |
| Student Registration      | `register.html`            | Public  |
| Student Login             | `student_login.html`       | Public  |
| Admin Login               | `admin_login.html`         | Public  |
| Routes Listing            | `routes.html`              | Public  |
| Student Dashboard         | `dashboard.html`           | Student |
| Driver GPS Panel          | `driver_gps.html`          | Admin   |
| Admin Dashboard           | `admin.html`               | Admin   |
| Bus Deactivation Confirm  | `deactivate_confirm.html`  | Admin   |
| Students List             | `students.html`            | Admin   |
| Gate Logs Page            | `gate_logs.html`           | Admin   |
| Reports & Analytics       | `reports.html`             | Admin   |

---

## 💾 CSV Backup System

The application automatically generates CSV backup files whenever data is added or deleted. These files are saved in the project root directory.

| File                   | Contents                                      |
|------------------------|-----------------------------------------------|
| `backup_buses.csv`     | All bus records including driver information  |
| `backup_routes.csv`    | All route records with timing and stops       |
| `backup_users.csv`     | Student data (passwords are excluded)         |
| `backup_gate_logs.csv` | All gate entry and exit log records           |

Manual export is also available from the **Reports** page in the admin panel, with support for date range, bus, and entry type filters.

---

## 🔐 Security Notes (For Production)

The following improvements are strongly recommended before deploying this application to a live environment:

- [ ] Replace plain text passwords with hashed passwords using `werkzeug.security.generate_password_hash`
- [ ] Change `app.secret_key` to a long, randomly generated secure string
- [ ] Add CSRF protection using `Flask-WTF`
- [ ] Store sensitive configuration values in environment variables using `python-dotenv`
- [ ] Migrate from SQLite to a production-grade database such as PostgreSQL or MySQL
- [ ] Enable HTTPS with a valid SSL/TLS certificate
- [ ] Implement rate limiting on login routes to prevent brute-force attacks

---

## 👨‍💻 Author

**Developed for:** CDIPS College, Indore (Madhya Pradesh, India)  
**Academic Year:** 2025–2026  
**Stack:** Python · Flask · SQLite · HTML5/CSS3 · JavaScript · Chart.js · Leaflet.js

---

> © 2026 College Bus Tracking System — CDIPS, Indore (M.P.)
