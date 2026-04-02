# 🚌 College Bus Tracking System - CDIPS Indore
## Flask + SQLite Backend - Current Implementation

---

## ✅ Project Overview
This project is a Flask-based college bus tracking system with:
- separate **Admin** and **Student** login flows
- dashboard views for students and administrators
- SQLite database persistence (`bus_tracker.db`)
- bus activation/deactivation with route fallback
- notifications and gate log tracking

---

## 📁 Project Structure

```
./
├── app.py                  ← Flask backend (main app)
├── bus_tracker.db          ← SQLite database (created automatically)
├── check_data.py           ← DB inspection helper script
├── requirements.txt
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── admin.html
    ├── admin_login.html
    ├── base.html
    ├── dashboard.html
    ├── deactivate_confirm.html
    ├── gate_logs.html
    ├── home.html
    ├── register.html
    ├── routes.html
    ├── student_login.html
    └── students.html
```

---

## ▶️ How to Run

### Step 1: Install dependencies
```bash
pip install flask
```

### Step 2: Start the app
```bash
python app.py
```

### Step 3: Open in browser
```text
http://localhost:5000
```

---

## 🔐 Login & Registration

### Admin Login
- **URL**: `http://localhost:5000/admin/login`
- **Email**: `admin@cdips.edu`
- **Password**: `admin123`
- **Role**: `admin`

### Student Login
- **URL**: `http://localhost:5000/student/login`
- Students must first register at `http://localhost:5000/register`
- **Role**: `student`

### Login Redirect
- `/login` redirects to `/student/login`

---

## 📋 Core Pages & Routes

| Page              | URL                   | Description |
|-------------------|-----------------------|-------------|
| Home              | `/`                   | Landing page with system stats |
| Student Login     | `/student/login`      | Student login form |
| Admin Login       | `/admin/login`        | Admin login form |
| Register          | `/register`           | Student registration form |
| Student Dashboard | `/dashboard`          | Student details, route & notifications |
| Admin Panel       | `/admin`              | Manage buses, students, routes, logs |
| Students List     | `/admin/students`     | Student search/filter page |
| Gate Logs         | `/admin/gate-logs`    | Bus entry/exit log management |
| Routes Info       | `/routes-info`        | All routes and assigned buses |
| Deactivate Bus     | `/admin/bus-status/<id>/inactive` | Bus deactivation confirmation |
| Activate Bus      | `/admin/bus-status/<id>/active`   | Reactivate bus |

---

## ✨ Key Features

- Separate admin and student authentication
- Student registration with validation:
  - name only letters and spaces
  - valid email
  - password with letter, number, special character
  - 10-digit phone number
  - route selection
- Admin dashboard for managing:
  - buses
  - routes
  - students
  - gate logs
- Bus deactivation with optional alternate bus assignment
- Notification system for affected students
- Student dashboard with route assignment details
- Route repair endpoint for restoring seed bus assignments
- Search and filter students by name/email/route

---

## 🗄️ Database Schema

- `users` — student/admin accounts
- `buses` — bus details, driver info, status
- `routes` — route metadata, start/end points, stops
- `gate_logs` — bus entry/exit records
- `notifications` — student notifications

---

## 🧪 Helper Script

Use `check_data.py` to inspect current database contents:
```bash
python check_data.py
```

---

## 💡 Notes

- The app creates `bus_tracker.db` automatically on first run.
- Admin account is seeded automatically if it does not exist.
- Student accounts are stored with `role='student'`.
- Bus and route seed data are inserted when the database is empty.
- Notifications are generated when buses are deactivated or reactivated.

---

## 📞 Support

For issues or questions, update the docs or contact the developer.

© 2026 CDIPS Indore - Bus Tracking System
