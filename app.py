import csv
import io
from datetime import datetime
import pytz

from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import sqlite3, re
from functools import wraps

app = Flask(__name__)
app.secret_key = 'bustrack_cdips_2026'
DB = 'bus_tracker.db'

# ─── DATABASE ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT DEFAULT 'student',
        phone TEXT, route_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_number TEXT UNIQUE NOT NULL, driver_name TEXT NOT NULL,
        driver_phone TEXT, driver_address TEXT, capacity INTEGER DEFAULT 40,
        status TEXT DEFAULT 'active',
        current_lat REAL DEFAULT 22.7196, current_lng REAL DEFAULT 75.8577)''')
    # Migration: driver_address column add karo agar nahi hai
    try:
        c.execute("ALTER TABLE buses ADD COLUMN driver_address TEXT")
    except Exception:
        pass  # Column already exists
    c.execute('''CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_name TEXT NOT NULL, bus_id INTEGER,
        original_bus_id INTEGER,
        start_point TEXT, end_point TEXT,
        departure_time TEXT, arrival_time TEXT, stops TEXT,
        FOREIGN KEY(bus_id) REFERENCES buses(id))''')
    # Migration: original_bus_id column add karo agar nahi hai
    try:
        c.execute("ALTER TABLE routes ADD COLUMN original_bus_id INTEGER")
    except Exception:
        pass  # Column already exists
    c.execute('''CREATE TABLE IF NOT EXISTS gate_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER, bus_number TEXT, entry_type TEXT,
        log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        noted_by TEXT DEFAULT 'System',
        FOREIGN KEY(bus_id) REFERENCES buses(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    # Seed data
    if not c.execute("SELECT 1 FROM users WHERE email='admin@cdips.edu'").fetchone():
        c.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                  ('Admin','admin@cdips.edu','admin123','admin'))
    if c.execute("SELECT COUNT(*) FROM buses").fetchone()[0] == 0:
        c.executemany("INSERT INTO buses(bus_number,driver_name,driver_phone,capacity,status) VALUES(?,?,?,?,?)",[
            ('BUS-01','Ramesh Kumar','9876543210',40,'active'),
            ('BUS-02','Suresh Patel','9876543211',45,'active'),
            ('BUS-03','Mahesh Singh','9876543212',40,'active')])
    if c.execute("SELECT COUNT(*) FROM routes").fetchone()[0] == 0:
        c.executemany("INSERT INTO routes(route_name,bus_id,start_point,end_point,departure_time,arrival_time,stops) VALUES(?,?,?,?,?,?,?)",[
            ('Route A - Vijay Nagar',1,'Vijay Nagar','CDIPS College','07:30','08:15','Vijay Nagar → Scheme 54 → Palasia → CDIPS'),
            ('Route B - Palasia',2,'Palasia','CDIPS College','07:45','08:20','Palasia → LIG Colony → Tilak Nagar → CDIPS'),
            ('Route C - Rajwada',3,'Rajwada','CDIPS College','07:15','08:10','Rajwada → Sarwate → Geeta Bhawan → CDIPS')])
    conn.commit(); conn.close()
    
def export_to_csv():
    """Export database tables to CSV files for backup"""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    
    # Export buses
    buses = conn.execute("SELECT * FROM buses").fetchall()
    with open('backup_buses.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'bus_number', 'driver_name', 'driver_phone', 'capacity', 'status'])
        for bus in buses:
            writer.writerow([bus['id'], bus['bus_number'], bus['driver_name'], bus['driver_phone'], bus['capacity'], bus['status']])
    
    # Export routes
    routes = conn.execute("SELECT * FROM routes").fetchall()
    with open('backup_routes.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'route_name', 'bus_id', 'original_bus_id','departure_time', 'arrival_time', 'stops'])
        for route in routes:
            writer.writerow([route['id'], route['route_name'], route['bus_id'], route['original_bus_id'], route['departure_time'], route['arrival_time'], route['stops']])
    
    # Export users (only students, exclude password and admin data)
    users = conn.execute("SELECT * FROM users WHERE role='student'").fetchall()
    with open('backup_users.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'phone', 'route_id'])
        for user in users:
            writer.writerow([user['name'], user['email'], user['phone'], user['route_id']])

    # Export gate_logs with bus details
    gate_logs = conn.execute("""
        SELECT gl.id, gl.bus_id, b.bus_number, gl.entry_type, gl.log_time
        FROM gate_logs gl
        LEFT JOIN buses b ON gl.bus_id = b.id
    """).fetchall()
    with open('backup_gate_logs.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'bus_id', 'bus_number', 'entry_type', 'log_time'])
        for log in gate_logs:
            writer.writerow([log['id'], log['bus_id'], log['bus_number'], log['entry_type'], log['log_time']])
    
    conn.close()

# ─── DECORATORS ────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'student' not in session:
            flash('Please login first.', 'error')
            return redirect(url_for('student_login'))
        return f(*a, **kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'admin' not in session:
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*a, **kw)
    return dec

# ─── PUBLIC ────────────────────────────────────────────────────────────
@app.route('/')
def home():
    db = get_db()
    stats = dict(buses=db.execute("SELECT COUNT(*) FROM buses").fetchone()[0],
                 students=db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
                 routes=db.execute("SELECT COUNT(*) FROM routes").fetchone()[0])
    db.close(); return render_template('home.html', stats=stats)

@app.route('/routes-info')
def routes_page():
    db = get_db()
    routes = db.execute('''SELECT r.*,b.bus_number,b.driver_name,b.status
                           FROM routes r LEFT JOIN buses b ON r.bus_id=b.id''').fetchall()
    db.close(); return render_template('routes.html', routes=routes)

# ─── AUTH - ADMIN LOGIN ────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        pw    = request.form['password'].strip()
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE email=? AND password=? AND role='admin'", (email,pw)).fetchone()
        db.close()
        if u:
            session['admin'] = {
                'id': u['id'],
                'name': u['name'],
                'email': u['email']
                }
            flash(f'Welcome, {u["name"]}!','success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.','error')
    return render_template('admin_login.html')

# ─── AUTH - STUDENT LOGIN ──────────────────────────────────────────────
@app.route('/student/login', methods=['GET','POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        pw    = request.form['password'].strip()
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE email=? AND password=? AND role='student'", (email,pw)).fetchone()
        db.close()
        if u:
            session['student'] = {
                'id': u['id'],
                'name': u['name'],
                'email': u['email'],
                }
            flash(f'Welcome, {u["name"]}!','success')
            return redirect(url_for('dashboard'))
        flash('Invalid student credentials.','error')
    return render_template('student_login.html')

# ─── AUTH - OLD LOGIN ROUTE (Redirect) ─────────────────────────────────
@app.route('/login')
def login():
    # Redirect to student login by default
    flash('Please choose your login type.','info')
    return redirect(url_for('student_login'))

@app.route('/register', methods=['GET','POST'])
def register():   
    db = get_db()
    routes = db.execute("SELECT * FROM routes").fetchall()
    if request.method == 'POST':
        name=request.form['name'].strip(); email=request.form['email'].strip()
        pw=request.form['password'].strip(); phone=request.form['phone'].strip()
        confirm_pw=request.form.get('confirm_password','').strip()
        route_id=request.form.get('route_id') or None
        errors=[]
        # Name → only alphabets (space allowed)
        if not re.match(r'^[A-Za-z ]{3,}$', name):
            errors.append('Name must contain only alphabets and be at least 3 characters.')
        # Email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email):
            errors.append('Enter a valid email (e.g. suyog@gmail.com).')
        # Password
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&]).{6,}$', pw):
            errors.append('Password must be at least 6 characters and include letter, number, and special character.')
        # Confirm password
        if pw != confirm_pw:
            errors.append('Passwords do not match.')
        # Phone
        if not phone.isdigit():
            errors.append('Phone must contain only numbers (no alphabets or special characters).')
        elif len(phone) != 10:
            errors.append('Phone must be exactly 10 digits.')
        if not route_id:
            errors.append('Please select a route.')

        for e in errors: flash(e,'error')
        if not errors:
            try:
                db.execute("INSERT INTO users(name,email,password,phone,role,route_id) VALUES(?,?,?,?,?,?)",
                           (name,email,pw,phone,'student',route_id))
                db.commit();
                export_to_csv()  # Backup ke liye CSV export
                db.close()
                flash('Registration successful! Please login.','success')
                return redirect(url_for('student_login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.','error')
                return redirect(url_for('register'))
        return redirect(url_for('register'))
    db.close(); return render_template('register.html', routes=routes)

@app.route('/logout/student')
def logout_student():
    session.pop('student', None)
    flash('Student logged out.', 'success')
    return redirect(url_for('student_login'))

@app.route('/logout/admin')
def logout_admin():
    session.pop('admin', None)
    flash('Admin logged out.', 'success')
    return redirect(url_for('admin_login'))

# ─── STUDENT DASHBOARD ─────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['student']['id'],)).fetchone()
    my_route = None
    if user['route_id']:
        my_route = db.execute('''SELECT r.*,b.bus_number,b.driver_name,b.driver_phone,b.driver_address,b.status
                                 FROM routes r LEFT JOIN buses b ON r.bus_id=b.id
                                 WHERE r.id=?''', (user['route_id'],)).fetchone()
    all_routes = db.execute("SELECT * FROM routes").fetchall()
    db.close(); return render_template('dashboard.html', user=user, my_route=my_route, all_routes=all_routes)

# ─── ADMIN DASHBOARD ───────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    buses    = db.execute("SELECT * FROM buses").fetchall()
    students = db.execute('''SELECT u.*,r.route_name FROM users u
                             LEFT JOIN routes r ON u.route_id=r.id
                             WHERE u.role='student' ORDER BY u.created_at DESC''').fetchall()
    routes   = db.execute("SELECT r.*,b.bus_number FROM routes r LEFT JOIN buses b ON r.bus_id=b.id").fetchall()
    logs     = db.execute("SELECT * FROM gate_logs ORDER BY log_time DESC LIMIT 15").fetchall()
    stats = dict(
        total_buses=db.execute("SELECT COUNT(*) FROM buses").fetchone()[0],
        total_students=db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        total_routes=db.execute("SELECT COUNT(*) FROM routes").fetchone()[0],
        today_logs=db.execute("SELECT COUNT(*) FROM gate_logs WHERE DATE(log_time)=DATE('now')").fetchone()[0])
    db.close(); return render_template('admin.html', buses=buses, students=students, routes=routes, logs=logs, stats=stats)

@app.route('/admin/add-bus', methods=['POST'])
@admin_required
def add_bus():
    bus_num=request.form['bus_number'].strip(); driver=request.form['driver_name'].strip()
    phone=request.form.get('driver_phone','').strip(); cap=request.form.get('capacity',40)
    address=request.form.get('driver_address','').strip()
    db=get_db()
    try:
        db.execute("INSERT INTO buses(bus_number,driver_name,driver_phone,driver_address,capacity) VALUES(?,?,?,?,?)",(bus_num,driver,phone,address,cap))
        db.commit(); export_to_csv()  # Backup ke liye CSV export
        flash(f'Bus {bus_num} added.','success')
    except sqlite3.IntegrityError:
        flash('Bus number already exists.','error')
    db.close(); return redirect(url_for('admin_dashboard')+'#buses')

@app.route('/admin/delete-bus/<int:bid>')
@admin_required
def delete_bus(bid):
    db=get_db(); db.execute("DELETE FROM buses WHERE id=?",(bid,)); db.commit(); export_to_csv()  # Backup ke liye CSV export
    db.close()
    flash('Bus deleted.','success'); return redirect(url_for('admin_dashboard')+'#buses')

@app.route('/admin/delete-gate-log/<int:lid>')
@admin_required
def delete_gate_log(lid):
    db = get_db()
    db.execute("DELETE FROM gate_logs WHERE id=?", (lid,))
    db.commit(); db.close()
    flash('Gate log entry deleted.', 'success')
    # Referrer check: agar gate_logs page se aaye to wahi return karo
    ref = request.referrer or ''
    if 'gate-logs' in ref:
        return redirect(url_for('gate_logs_page'))
    return redirect(url_for('admin_dashboard') + '#logs')

@app.route('/admin/add-route', methods=['POST'])
@admin_required
def add_route():
    name=request.form['route_name'].strip(); bus_id=request.form.get('bus_id') or None
    dept=request.form.get('departure_time',''); arr=request.form.get('arrival_time','')
    stops=request.form.get('stops','')
    # Parse first and last stop
    stop_list = stops.replace(',','→').split('→')
    start = stop_list[0].strip() if stop_list else ''
    end   = stop_list[-1].strip() if stop_list else ''
    db=get_db()
    db.execute("INSERT INTO routes(route_name,bus_id,start_point,end_point,departure_time,arrival_time,stops) VALUES(?,?,?,?,?,?,?)",
               (name,bus_id,start,end,dept,arr,stops))
    db.commit();export_to_csv()  # Backup ke liye CSV export
    db.close()
    flash(f'Route "{name}" added.','success')
    return redirect(url_for('admin_dashboard')+'#routes')

@app.route('/admin/delete-route/<int:rid>')
@admin_required
def delete_route(rid):
    db=get_db(); db.execute("DELETE FROM routes WHERE id=?",(rid,)); db.commit(); export_to_csv()  # Backup ke liye CSV export
    db.close()
    flash('Route deleted.','success')
    return redirect(url_for('admin_dashboard')+'#routes')

# ─── BUS STATUS CHANGE WITH DEACTIVATION PAGE ──────────────────────────
@app.route('/admin/bus-status/<int:bid>/<status>', methods=['GET','POST'])
@admin_required
def bus_status(bid, status):
    db = get_db()
    bus = db.execute("SELECT * FROM buses WHERE id=?", (bid,)).fetchone()

    if not bus:
        flash('Bus not found.', 'error')
        db.close()
        return redirect(url_for('admin_dashboard'))

    # ✅ DEACTIVATION WITH CONFIRMATION PAGE
    if status == 'inactive':
        if request.method == 'GET':
            # Show deactivation confirmation page
            affected_routes = db.execute(
                "SELECT * FROM routes WHERE bus_id=?", (bid,)
            ).fetchall()

            active_buses = db.execute(
                "SELECT * FROM buses WHERE status='active' AND id!=?", (bid,)
            ).fetchall()

            db.close()
            return render_template(
                'deactivate_confirm.html',
                bus=bus,
                affected_routes=affected_routes,
                active_buses=active_buses
            )

        # POST: Process deactivation
        alt_bus_id = request.form.get('alt_bus_id', '').strip()
        reason = request.form.get('reason', 'other')

        # Deactivate bus
        db.execute("UPDATE buses SET status='inactive' WHERE id=?", (bid,))

        # Get affected routes
        affected_routes = db.execute(
            "SELECT * FROM routes WHERE bus_id=?", (bid,)
        ).fetchall()

        alt_bus = None
        if alt_bus_id:
            alt_bus = db.execute("SELECT * FROM buses WHERE id=?", (alt_bus_id,)).fetchone()
            # Assign alternate bus to routes (save original bus for restoration)
            db.execute(
                "UPDATE routes SET bus_id=?, original_bus_id=? WHERE bus_id=?",
                (alt_bus_id, bid, bid)
            )

        # Get affected students
        affected_students = db.execute(
            """SELECT DISTINCT u.id FROM users u
               JOIN routes r ON u.route_id = r.id
               WHERE r.bus_id = ? OR r.original_bus_id = ?
               AND u.role = 'student'""",
            (bid if not alt_bus_id else alt_bus_id, bid)
        ).fetchall()

        # Reason messages mapping
        reason_msgs = {
            'technical': 'due to a technical fault',
            'accident': 'due to an accident',
            'maintenance': 'for scheduled maintenance',
            'other': 'temporarily'
        }
        reason_text = reason_msgs.get(reason, 'temporarily')

        # Send notification
        if alt_bus:
            msg = (
                f"⚠️ Bus {bus['bus_number']} is unavailable {reason_text}. "
                f"You've been assigned alternate bus {alt_bus['bus_number']}. "
                f"Driver: {alt_bus['driver_name']} | Contact: {alt_bus['driver_phone'] or 'N/A'}.")
        else:
            msg = (
                f"⚠️ Bus {bus['bus_number']} is unavailable {reason_text}. "
                f"No alternate bus assigned yet. Please contact admin for updates.")

        for s in affected_students:
            db.execute("INSERT INTO notifications(user_id, message) VALUES(?,?)", (s['id'], msg))

        db.commit(); db.close()
        n = len(affected_students)
        flash(f'Bus {bus["bus_number"]} deactivated. '
              + (f'Alternate bus {alt_bus["bus_number"]} assigned. ' if alt_bus else '')
              + f'{n} student(s) notified.', 'success')

    else:  # Activate
        db.execute("UPDATE buses SET status='active' WHERE id=?", (bid,))

        # Woh routes wapas assign karo jinhe is bus se hataya gaya tha
        db.execute("UPDATE routes SET bus_id=?, original_bus_id=NULL WHERE original_bus_id=?",
                   (bid, bid))

        # Affected students dhundho (jo ab is bus ki route pe hain)
        affected_students = db.execute(
            """SELECT DISTINCT u.id FROM users u
               JOIN routes r ON u.route_id = r.id
               WHERE r.bus_id = ? AND u.role = 'student'""",
            (bid,)
        ).fetchall()

        msg = (
            f"✅ Bus {bus['bus_number']} is now operational. "
            f"Service on your route has resumed. "
            f"Driver: {bus['driver_name']} | Contact: {bus['driver_phone'] or 'N/A'}.")

        for s in affected_students:
            db.execute("INSERT INTO notifications(user_id, message) VALUES(?,?)", (s['id'], msg))

        db.commit(); db.close()
        n = len(affected_students)
        flash(f'Bus {bus["bus_number"]} has been activated. {n} student(s) have been notified.', 'success')


    return redirect(url_for('admin_dashboard')+'#buses')


# ─── NOTIFICATIONS ─────────────────────────────────────────────────────
@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    student_id = session['student']['id']
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (student_id,))
    db.commit(); db.close()
    return redirect(url_for('dashboard'))


@app.route('/notifications/delete/<int:nid>', methods=['POST'])
@login_required
def delete_notification(nid):
    student_id = session['student']['id']
    db = get_db()
    # Sirf apni notification delete kar sake — dusre ki nahi
    db.execute("DELETE FROM notifications WHERE id=? AND user_id=?", (nid, student_id))
    db.commit(); db.close()
    return redirect(url_for('dashboard'))


@app.route('/notifications/delete-all', methods=['POST'])
@login_required
def delete_all_notifications():
    student_id = session['student']['id']
    db = get_db()
    db.execute("DELETE FROM notifications WHERE user_id=?", (student_id,))
    db.commit(); db.close()
    return redirect(url_for('dashboard'))


@app.context_processor
def inject_notifications():
    if 'student' in session:
        student_id = session['student']['id']
        db = get_db()
        notifs = db.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (student_id,)
        ).fetchall()
        unread = db.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
            (student_id,)
        ).fetchone()[0]
        db.close()
        return dict(notifications=notifs, unread_count=unread)
    return dict(notifications=[], unread_count=0)

# ─── GATE LOG ──────────────────────────────────────────────────────────
@app.route('/admin/add-gate-log', methods=['POST'])
@admin_required
def add_gate_log():
    bus_id=request.form['bus_id']; entry_type=request.form['entry_type']
    # ✅ Automatic IST Current Time
    ist      = pytz.timezone('Asia/Kolkata')
    log_time = datetime.now(ist).strftime('%d %b %Y, %I:%M:%S %p')
    db=get_db()
    bus=db.execute("SELECT * FROM buses WHERE id=?", (bus_id,)).fetchone()
    if bus:
        db.execute("INSERT INTO gate_logs(bus_id,bus_number,entry_type,log_time,noted_by) VALUES(?,?,?,?,?)",
                   (bus_id,bus['bus_number'],entry_type,log_time,session['admin']['name']))
        db.commit();export_to_csv()  # Backup ke liye CSV export
        flash(f'Gate log: {bus["bus_number"]} - {entry_type}','success')
    db.close(); return redirect(url_for('admin_dashboard')+'#logs')

# ─── STUDENTS LIST (Data Display Page) ────────────────────────────────
@app.route('/admin/students')
@admin_required
def students_list():
    search=request.args.get('search',''); route_filter=request.args.get('route','')
    db=get_db()
    q = "SELECT u.*,r.route_name FROM users u LEFT JOIN routes r ON u.route_id=r.id WHERE u.role='student'"
    params=[]
    if search:
        q+=" AND (u.name LIKE ? OR u.email LIKE ?)"; params+=[f'%{search}%',f'%{search}%']
    if route_filter:
        q+=" AND u.route_id=?"; params.append(route_filter)
    q+=" ORDER BY u.created_at DESC"
    students=db.execute(q,params).fetchall()
    routes=db.execute("SELECT * FROM routes").fetchall()

    # Har student ki notifications bhi fetch karo
    student_ids = [s['id'] for s in students]
    notif_map = {}
    if student_ids:
        placeholders = ','.join('?' * len(student_ids))
        all_notifs = db.execute(
            f"SELECT * FROM notifications WHERE user_id IN ({placeholders}) ORDER BY created_at DESC",
            student_ids
        ).fetchall()
        for n in all_notifs:
            uid = n['user_id']
            if uid not in notif_map:
                notif_map[uid] = []
            notif_map[uid].append(n)

    notif_data = {
        str(uid): [
            {
                'msg': n['message'],
                'time': n['created_at'][:16] if n['created_at'] else '',
                'read': bool(n['is_read'])
            }
            for n in notif_map.get(uid, [])
        ]
        for uid in notif_map
    }
    student_names = {str(s['id']): s['name'] for s in students}
    db.close()
    return render_template('students.html', students=students, routes=routes,
                           search=search, route_filter=route_filter,
                           notif_map=notif_map,
                           notif_data=notif_data,
                           student_names=student_names)

@app.route('/admin/delete-student/<int:uid>')
@admin_required
def delete_student(uid):
    db=get_db(); db.execute("DELETE FROM users WHERE id=? AND role='student'",(uid,)); db.commit(); db.close()
    export_to_csv()  # Backup ke liye CSV export
    flash('Student removed.','success'); return redirect(url_for('students_list'))

# ─── GATE LOGS PAGE (Data Display Page) ───────────────────────────────
@app.route('/admin/gate-logs')
@admin_required
def gate_logs_page():
    db=get_db()
    logs=db.execute('''SELECT gl.*,b.driver_name FROM gate_logs gl
                       LEFT JOIN buses b ON gl.bus_id=b.id ORDER BY gl.log_time DESC''').fetchall()
    buses=db.execute("SELECT * FROM buses").fetchall()
    db.close(); return render_template('gate_logs.html', logs=logs, buses=buses)

# ─── ADMIN: ROUTE-BUS REPAIR ───────────────────────────────────────────
@app.route('/admin/fix-routes')
@admin_required
def fix_routes():
    
    db = get_db()
    # Har route ka original (seed) bus restore karo
    seed = db.execute("SELECT * FROM routes ORDER BY id").fetchall()
    buses = db.execute("SELECT * FROM buses ORDER BY id").fetchall()
    fixed = 0
    for i, route in enumerate(seed):
        if i < len(buses):
            orig_bus = buses[i]
            if route['bus_id'] != orig_bus['id']:
                db.execute("UPDATE routes SET bus_id=?, original_bus_id=NULL WHERE id=?",
                           (orig_bus['id'], route['id']))
                fixed += 1
    db.commit(); db.close()
    flash(f'Routes repair complete. {fixed} route(s) fixed.', 'success')
    return redirect(url_for('admin_dashboard') + '#buses')


# ─── ADMIN REPORTS PAGE ────────────────────────────────────────────
@app.route('/admin/reports')
@admin_required
def admin_reports():
    db = get_db()

    # Filters (GET params)
    date_from    = request.args.get('date_from', '')
    date_to      = request.args.get('date_to', '')
    bus_filter   = request.args.get('bus_id', '')
    entry_filter = request.args.get('entry_type', '')

    # ── Summary stats ──────────────────────────────────────────────
    total_students  = db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    total_buses     = db.execute("SELECT COUNT(*) FROM buses").fetchone()[0]
    active_buses    = db.execute("SELECT COUNT(*) FROM buses WHERE status='active'").fetchone()[0]
    inactive_buses  = total_buses - active_buses
    total_routes    = db.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
    total_logs      = db.execute("SELECT COUNT(*) FROM gate_logs").fetchone()[0]
    total_drivers   = db.execute("SELECT COUNT(*) FROM buses").fetchone()[0]  # har bus ka ek driver

    # ── Chart data: Gate logs per bus ──────────────────────────────
    logs_per_bus = db.execute("""
        SELECT b.bus_number, COUNT(gl.id) as log_count
        FROM buses b
        LEFT JOIN gate_logs gl ON b.id = gl.bus_id
        GROUP BY b.id, b.bus_number
        ORDER BY log_count DESC
    """).fetchall()

    # ── Chart data: Entry vs Exit totals ───────────────────────────
    entry_count = db.execute("SELECT COUNT(*) FROM gate_logs WHERE entry_type='Entry'").fetchone()[0]
    exit_count  = db.execute("SELECT COUNT(*) FROM gate_logs WHERE entry_type='Exit'").fetchone()[0]

    # ── Chart data: Students per route ─────────────────────────────
    route_students = db.execute("""
        SELECT r.route_name, COUNT(u.id) as student_count
        FROM routes r
        LEFT JOIN users u ON r.id = u.route_id AND u.role = 'student'
        GROUP BY r.id, r.route_name
    """).fetchall()

    # ── Filtered gate logs for table ───────────────────────────────
    buses = db.execute("SELECT * FROM buses").fetchall()

    q      = """SELECT gl.*, b.driver_name FROM gate_logs gl
                LEFT JOIN buses b ON gl.bus_id = b.id WHERE 1=1"""
    params = []

    if date_from:
        q += " AND DATE(gl.log_time) >= ?"
        params.append(date_from)
    if date_to:
        q += " AND DATE(gl.log_time) <= ?"
        params.append(date_to)
    if bus_filter:
        q += " AND gl.bus_id = ?"
        params.append(bus_filter)
    if entry_filter:
        q += " AND gl.entry_type = ?"
        params.append(entry_filter)

    q += " ORDER BY gl.log_time DESC"
    filtered_logs = db.execute(q, params).fetchall()
    db.close()

    return render_template('reports.html',
        total_students  = total_students,
        total_buses     = total_buses,
        active_buses    = active_buses,
        inactive_buses  = inactive_buses,
        total_routes    = total_routes,
        total_logs      = total_logs,
        logs_per_bus    = logs_per_bus,
        entry_count     = entry_count,
        exit_count      = exit_count,
        route_students  = route_students,
        filtered_logs   = filtered_logs,
        buses           = buses,
        date_from       = date_from,
        date_to         = date_to,
        bus_filter      = bus_filter,
        entry_filter    = entry_filter,
        total_drivers   = total_drivers,
    )

# ─── EXPORT REPORT AS CSV ─────────────────────────────────────────
@app.route('/admin/reports/export')
@admin_required
def export_report():
    db = get_db()

    # Same filters as reports page
    date_from    = request.args.get('date_from', '')
    date_to      = request.args.get('date_to', '')
    bus_filter   = request.args.get('bus_id', '')
    entry_filter = request.args.get('entry_type', '')

    q      = """SELECT gl.id, gl.bus_number, b.driver_name, gl.entry_type,
                       gl.log_time, gl.noted_by
                FROM gate_logs gl
                LEFT JOIN buses b ON gl.bus_id = b.id WHERE 1=1"""
    params = []

    if date_from:
        q += " AND DATE(gl.log_time) >= ?"
        params.append(date_from)
    if date_to:
        q += " AND DATE(gl.log_time) <= ?"
        params.append(date_to)
    if bus_filter:
        q += " AND gl.bus_id = ?"
        params.append(bus_filter)
    if entry_filter:
        q += " AND gl.entry_type = ?"
        params.append(entry_filter)

    q += " ORDER BY gl.log_time DESC"
    logs = db.execute(q, params).fetchall()
    db.close()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bus Number', 'Driver Name', 'Entry Type', 'Log Time', 'Logged By'])
    for row in logs:
        writer.writerow([row['bus_number'], row['driver_name'] or '',
                         row['entry_type'], row['log_time'], row['noted_by']])

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=gate_logs_report.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


# ─── EXPORT DRIVERS BACKUP CSV ────────────────────────────────────
@app.route('/admin/reports/export-drivers')
@admin_required
def export_drivers():
    """Driver ka alag backup CSV — name, phone, address"""
    from datetime import datetime

    db = get_db()
    buses = db.execute('''
        SELECT bus_number, driver_name, driver_phone, driver_address, capacity, status
        FROM buses
        ORDER BY bus_number
    ''').fetchall()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bus Number', 'Driver Name', 'Driver Phone', 'Driver Address', 'Bus Capacity', 'Bus Status'])
    for b in buses:
        writer.writerow([
            b['bus_number']     or '',
            b['driver_name']    or '',
            b['driver_phone']   or '',
            b['driver_address'] or '',
            b['capacity']       or '',
            b['status']         or ''
        ])

    filename = f"driver_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = make_response(output.getvalue())
    response.headers['Content-Type']        = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response




if __name__ == '__main__':
    init_db(); app.run(debug=True, port=5000)
