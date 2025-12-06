from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import secrets

app = Flask(__name__)
app.secret_key = "change_me_super_secret"

# ==================================================
# HELPERS: AUTH & ROLES
# ==================================================

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash("Access denied for this portal.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def current_user_id():
    return session.get('user_id')


# ==================================================
# ROOT
# ==================================================

@app.route('/')
def root():
    role = session.get('role')
    if role == 'parent':
        return redirect(url_for('parent_dashboard'))
    if role == 'provider':
        return redirect(url_for('provider_scan'))
    if role == 'admin':
        return redirect(url_for('admin_stats'))
    return redirect(url_for('login'))


# ==================================================
# AUTH: PARENT SIGNUP, LOGIN, LOGOUT
# ==================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email'].lower()
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Passwords do not match", "danger")
        else:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                flash("Email already registered", "danger")
            else:
                hashed = generate_password_hash(password)
                cur.execute(
                    "INSERT INTO users(name, email, password, role) VALUES (%s,%s,%s,'parent')",
                    (name, email, hashed),
                )
                conn.commit()
                flash("Signup successful. Please login.", "success")
                return redirect(url_for('login'))
            cur.close()
            conn.close()

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['role'] = user['role']

            if user['role'] == 'parent':
                return redirect(url_for('parent_dashboard'))
            elif user['role'] == 'provider':
                return redirect(url_for('provider_scan'))
            else:
                return redirect(url_for('admin_stats'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))


# ==================================================
# PARENT PORTAL
# ==================================================

@app.route('/parent/dashboard')
@roles_required('parent', 'admin')
def parent_dashboard():
    user_id = current_user_id()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM child WHERE user_id=%s", (user_id,))
    children_count = cur.fetchone()['c']

    cur.execute(
        """
        SELECT COUNT(*) AS given
        FROM vaccination_record vr
        JOIN child c ON vr.child_id = c.child_id
        WHERE c.user_id=%s
        """,
        (user_id,),
    )
    given = cur.fetchone()['given']
    pending_vaccines = max(children_count * 10 - given, 0)

    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM qr_access q
        JOIN child c ON q.child_id=c.child_id
        WHERE c.user_id=%s AND q.is_active=1
        """,
        (user_id,),
    )
    active_qr = cur.fetchone()['c']

    cur.execute("SELECT * FROM child WHERE user_id=%s", (user_id,))
    children = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'parent_dashboard.html',
        portal='parent',
        name=session.get('name'),
        children=children,
        children_count=children_count,
        pending_vaccines=pending_vaccines,
        active_qr=active_qr,
    )


@app.route('/parent/children')
@roles_required('parent', 'admin')
def children_list():
    user_id = current_user_id()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM child WHERE user_id=%s", (user_id,))
    children = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('children.html', portal='parent', children=children)


@app.route('/parent/child/add', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def child_add():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO child(
                name, dob, passport_number, current_country,
                parent_mailid, parent_primary_mobile_no, user_id
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                request.form['name'],
                request.form['dob'],
                request.form['passport'],
                request.form['country'],
                request.form['parent_email'],
                request.form['phone'],
                current_user_id(),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Child added.", "success")
        return redirect(url_for('children_list'))

    return render_template('child_form.html', portal='parent', mode='add')


@app.route('/parent/child/<int:child_id>/edit', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def child_edit(child_id):
    conn = get_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        cur.execute(
            """
            UPDATE child
            SET name=%s, dob=%s, passport_number=%s, current_country=%s,
                parent_mailid=%s, parent_primary_mobile_no=%s
            WHERE child_id=%s
            """,
            (
                request.form['name'],
                request.form['dob'],
                request.form['passport'],
                request.form['country'],
                request.form['parent_email'],
                request.form['phone'],
                child_id,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Child updated.", "success")
        return redirect(url_for('children_list'))

    cur.execute("SELECT * FROM child WHERE child_id=%s", (child_id,))
    child = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('child_form.html', portal='parent', mode='edit', child=child)


@app.route('/parent/child/<int:child_id>/delete')
@roles_required('parent', 'admin')
def child_delete(child_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM child WHERE child_id=%s", (child_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Child deleted.", "info")
    return redirect(url_for('children_list'))


@app.route('/parent/child/<int:child_id>')
@roles_required('parent', 'admin')
def child_detail(child_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM child WHERE child_id=%s", (child_id,))
    child = cur.fetchone()

    cur.execute(
        """
        SELECT vr.*, v.vaccine_name
        FROM vaccination_record vr
        JOIN vaccine v ON vr.vaccine_id=v.vaccine_id
        WHERE vr.child_id=%s
        ORDER BY vr.date_given DESC
        """,
        (child_id,),
    )
    vaccinations = cur.fetchall()

    cur.execute("SELECT * FROM travel WHERE child_id=%s ORDER BY travel_date DESC", (child_id,))
    travels = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'child_detail.html',
        portal='parent',
        child=child,
        vaccinations=vaccinations,
        travels=travels,
    )


# ---------- VACCINATION ----------

@app.route('/parent/vaccination/add', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def vaccination_add():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            INSERT INTO vaccination_record(
                child_id, vaccine_id, dose_number, date_given,
                country_given, clinic_unique_name
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                request.form['child_id'],
                request.form['vaccine_id'],
                request.form['dose_number'],
                request.form['date_given'],
                request.form['country_given'],
                request.form['clinic_name'],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Vaccination recorded.", "success")
        return redirect(url_for('parent_dashboard'))

    user_id = current_user_id()
    cur.execute("SELECT child_id, name FROM child WHERE user_id=%s", (user_id,))
    children = cur.fetchall()
    cur.execute("SELECT vaccine_id, vaccine_name FROM vaccine")
    vaccines = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('vacc_form.html', portal='parent', children=children, vaccines=vaccines)


@app.route('/parent/vaccination/<int:record_id>/edit', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def vaccination_edit(record_id):
    conn = get_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        cur.execute("""
            UPDATE vaccination_record 
            SET vaccine_id=%s, dose_number=%s, date_given=%s, country_given=%s, clinic_unique_name=%s
            WHERE record_id=%s
        """, (
            request.form['vaccine_id'],
            request.form['dose_number'],
            request.form['date_given'],
            request.form['country_given'],
            request.form['clinic_name'],
            record_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        flash("Vaccination updated.", "success")
        return redirect(url_for('parent_dashboard'))
    
    cur.execute("SELECT * FROM vaccination_record WHERE record_id=%s", (record_id,))
    record = cur.fetchone()
    cur.execute("SELECT vaccine_id, vaccine_name FROM vaccine")
    vaccines = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('vacc_edit.html', portal='parent', record=record, vaccines=vaccines)


@app.route('/parent/vaccination/<int:record_id>/delete')
@roles_required('parent', 'admin')
def vaccination_delete(record_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vaccination_record WHERE record_id=%s", (record_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Vaccination deleted.", "info")
    return redirect(url_for('parent_dashboard'))


# ---------- TRAVEL ----------

@app.route('/parent/travel/add', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def travel_add():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            INSERT INTO travel(
                child_id, destination_country, travel_date, return_date
            )
            VALUES (%s,%s,%s,%s)
            """,
            (
                request.form['child_id'],
                request.form['destination'],
                request.form['travel_date'],
                request.form['return_date'] or None,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Travel plan added.", "success")
        return redirect(url_for('parent_dashboard'))

    user_id = current_user_id()
    cur.execute("SELECT child_id, name FROM child WHERE user_id=%s", (user_id,))
    children = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('travel_form.html', portal='parent', children=children)


# ---------- TRAVEL ADVISORY ----------

@app.route('/parent/travel/advisory/<int:trip_id>')
@roles_required('parent', 'admin')
def travel_advisory(trip_id):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM travel WHERE trip_id=%s", (trip_id,))
    trip = cur.fetchone()
    
    if not trip:
        flash("Travel plan not found.", "danger")
        return redirect(url_for('parent_dashboard'))
    
    cur.execute("""
        SELECT v.vaccine_id, v.vaccine_name 
        FROM country_vaccine_req cr
        JOIN vaccine v ON cr.vaccine_id = v.vaccine_id
        WHERE cr.country = %s
    """, (trip['destination_country'],))
    required = cur.fetchall()
    
    cur.execute("""
        SELECT vaccine_id FROM vaccination_record 
        WHERE child_id = %s
    """, (trip['child_id'],))
    given = [r['vaccine_id'] for r in cur.fetchall()]
    
    missing = [v for v in required if v['vaccine_id'] not in given]
    
    cur.execute("SELECT name FROM child WHERE child_id=%s", (trip['child_id'],))
    child = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return render_template('travel_advisory.html', 
        portal='parent',
        trip=trip, 
        child=child,
        required=required,
        missing=missing
    )


# ---------- QR CODES ----------

@app.route('/parent/qr', methods=['GET', 'POST'])
@roles_required('parent', 'admin')
def qr_codes():
    user_id = current_user_id()
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        child_id = request.form['child_id']
        qr_hash = secrets.token_hex(32)
        created = datetime.now()
        expiry = created + timedelta(days=30)

        cur.execute(
            """
            INSERT INTO qr_access(
                child_id, qr_code_hash, created_date, expiry_date, is_active
            )
            VALUES (%s,%s,%s,%s,1)
            """,
            (child_id, qr_hash, created, expiry),
        )
        conn.commit()
        flash("QR code generated.", "success")

    cur.execute("SELECT child_id, name FROM child WHERE user_id=%s", (user_id,))
    children = cur.fetchall()

    cur.execute(
        """
        SELECT q.*, c.name AS child_name
        FROM qr_access q
        JOIN child c ON q.child_id=c.child_id
        WHERE c.user_id=%s
        ORDER BY q.created_date DESC
        """,
        (user_id,),
    )
    qrs = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('qr_codes.html', portal='parent', children=children, qrs=qrs)


@app.route('/parent/qr_toggle/<int:qr_id>')
@roles_required('parent', 'admin')
def qr_toggle(qr_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_active FROM qr_access WHERE qr_id=%s", (qr_id,))
    row = cur.fetchone()
    if row:
        new_val = 0 if row['is_active'] else 1
        cur.execute("UPDATE qr_access SET is_active=%s WHERE qr_id=%s", (new_val, qr_id))
        conn.commit()
        flash("QR status updated.", "success")
    cur.close()
    conn.close()
    return redirect(url_for('qr_codes'))


@app.route('/parent/qr_delete/<int:qr_id>')
@roles_required('parent', 'admin')
def qr_delete(qr_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM qr_access WHERE qr_id=%s", (qr_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("QR deleted.", "info")
    return redirect(url_for('qr_codes'))


# ==================================================
# HEALTHCARE PROVIDER PORTAL
# ==================================================

@app.route('/provider/scan', methods=['GET', 'POST'])
@roles_required('provider', 'admin')
def provider_scan():
    result = None
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        qr_hash = request.form['qr_hash'].strip()

        cur.execute(
            """
            SELECT q.*, c.name, c.dob, c.current_country
            FROM qr_access q
            JOIN child c ON q.child_id = c.child_id
            WHERE qr_code_hash=%s
            """,
            (qr_hash,),
        )
        qr = cur.fetchone()

        if not qr:
            result = ("invalid", "QR not found")
        else:
            now = datetime.now()
            if not qr['is_active']:
                result = ("invalid", "QR deactivated")
            elif now > qr['expiry_date']:
                result = ("invalid", "QR expired")
            else:
                cur.execute(
                    """
                    SELECT v.vaccine_name, vr.dose_number, vr.date_given
                    FROM vaccination_record vr
                    JOIN vaccine v ON vr.vaccine_id=v.vaccine_id
                    WHERE vr.child_id=%s
                    ORDER BY vr.date_given DESC
                    """,
                    (qr['child_id'],),
                )
                vaccs = cur.fetchall()
                result = ("valid", {"qr": qr, "vaccs": vaccs})

                cur.execute(
                    """
                    INSERT INTO verification_log(provider_id, child_id, qr_id, status)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (current_user_id(), qr['child_id'], qr['qr_id'], 'valid'),
                )
                cur.execute(
                    "UPDATE qr_access SET access_count=access_count+1 WHERE qr_id=%s",
                    (qr['qr_id'],),
                )
                conn.commit()

    cur.close()
    conn.close()
    return render_template('provider_scan.html', portal='provider', result=result)


@app.route('/provider/log')
@roles_required('provider', 'admin')
def provider_log():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.*, u.name AS provider_name, c.name AS child_name
        FROM verification_log l
        LEFT JOIN users u ON l.provider_id=u.user_id
        LEFT JOIN child c ON l.child_id=c.child_id
        ORDER BY l.created_at DESC
        """
    )
    logs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('provider_log.html', portal='provider', logs=logs)


# ==================================================
# ADMIN PORTAL
# ==================================================

@app.route('/admin/stats')
@roles_required('admin')
def admin_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM child")
    total_children = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM vaccination_record")
    total_vaccines = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM qr_access WHERE is_active=1")
    active_qr = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM travel")
    travel_plans = cur.fetchone()['c']

    cur.close()
    conn.close()

    return render_template(
        'admin_stats.html',
        portal='admin',
        total_children=total_children,
        total_vaccines=total_vaccines,
        active_qr=active_qr,
        travel_plans=travel_plans,
    )


@app.route('/admin/vaccines', methods=['GET', 'POST'])
@roles_required('admin')
def admin_vaccines():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            INSERT INTO vaccine(vaccine_name, doses_required, min_age_months)
            VALUES (%s,%s,%s)
            """,
            (
                request.form['vaccine_name'],
                request.form['doses_required'],
                request.form['min_age_months'],
            ),
        )
        conn.commit()
        flash("Vaccine added.", "success")

    cur.execute("SELECT * FROM vaccine")
    vaccines = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_vaccines.html', portal='admin', vaccines=vaccines)


@app.route('/admin/vaccine/<int:vaccine_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_vaccine_edit(vaccine_id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        cur.execute(
            """
            UPDATE vaccine
            SET vaccine_name=%s, doses_required=%s, min_age_months=%s
            WHERE vaccine_id=%s
            """,
            (
                request.form['vaccine_name'],
                request.form['doses_required'],
                request.form['min_age_months'],
                vaccine_id,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Vaccine updated.", "success")
        return redirect(url_for('admin_vaccines'))

    cur.execute("SELECT * FROM vaccine WHERE vaccine_id=%s", (vaccine_id,))
    vaccine = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('admin_vaccines.html', portal='admin', edit_vaccine=vaccine)


@app.route('/admin/vaccine/<int:vaccine_id>/delete')
@roles_required('admin')
def admin_vaccine_delete(vaccine_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vaccine WHERE vaccine_id=%s", (vaccine_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Vaccine deleted.", "info")
    return redirect(url_for('admin_vaccines'))


# ==================================================
# MAIN
# ==================================================

if __name__ == '__main__':
    app.run(debug=True, port=5001)
