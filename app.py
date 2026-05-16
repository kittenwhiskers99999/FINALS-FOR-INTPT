from flask import Flask, request, redirect, url_for, session, render_template
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'change-this-secret'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='spotifind'
    )



def attach_photos(cursor, items, item_type):
    """Attach list of photos to each item."""
    if not items:
        return items
    # Convert to plain dicts so they are mutable
    items = [dict(i) for i in items]
    ids = [i['id'] for i in items]
    fmt = ','.join(['%s'] * len(ids))
    cursor.execute(
        f'SELECT * FROM item_photos WHERE item_id IN ({fmt}) AND item_type = %s ORDER BY uploaded_at ASC',
        ids + [item_type]
    )
    photos = cursor.fetchall()
    photo_map = {}
    for p in photos:
        photo_map.setdefault(p['item_id'], []).append(p['filename'])
    for item in items:
        item['photos'] = photo_map.get(item['id'], [item['image']] if item['image'] else [])
    return items

# =========================
# ROUTES
# =========================
@app.route('/', methods=['GET', 'POST'])
def index():
    if session.get('username'):
        return redirect(url_for('homepage'))

    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            message = 'Please enter both username and password.'
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                cursor.close()
                db.close()

                if not user or not check_password_hash(user['password'], password):
                    message = 'Invalid username or password.'
                else:
                    session['username'] = username
                    return redirect(url_for('homepage'))

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('login.html', title='Login', message=message)


@app.route('/home')
def homepage():
    if not session.get('username'):
        return redirect(url_for('index'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('''SELECT i.*, u.username AS reporter_name FROM lost_items i LEFT JOIN users u ON i.user_id = u.id WHERE i.status = %s ORDER BY i.reported_at DESC''', ('active',))
        lost_items = cursor.fetchall()
        cursor.execute('''SELECT i.*, u.username AS reporter_name FROM found_items i LEFT JOIN users u ON i.user_id = u.id WHERE i.status = %s ORDER BY i.reported_at DESC''', ('active',))
        found_items = cursor.fetchall()
        lost_items = attach_photos(cursor, lost_items, 'lost')
        found_items = attach_photos(cursor, found_items, 'found')
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
        found_items = []
        current_user_id = None
    return render_template('home.html', lost_items=lost_items, found_items=found_items, active='all', current_user_id=current_user_id)


@app.route('/lost')
def lost_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('''SELECT i.*, u.username AS reporter_name FROM lost_items i LEFT JOIN users u ON i.user_id = u.id WHERE i.status = %s ORDER BY i.reported_at DESC''', ('active',))
        lost_items = cursor.fetchall()
        lost_items = attach_photos(cursor, lost_items, 'lost')
        cursor.execute('SELECT id FROM users WHERE username = %s', (session.get('username'),))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        lost_items = []
        current_user_id = None
    return render_template('home.html', lost_items=lost_items, found_items=[], active='lost', current_user_id=current_user_id)


@app.route('/found')
def found_page():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('''SELECT i.*, u.username AS reporter_name FROM found_items i LEFT JOIN users u ON i.user_id = u.id WHERE i.status = %s ORDER BY i.reported_at DESC''', ('active',))
        found_items = cursor.fetchall()
        found_items = attach_photos(cursor, found_items, 'found')
        cursor.execute('SELECT id FROM users WHERE username = %s', (session.get('username'),))
        u = cursor.fetchone()
        current_user_id = u['id'] if u else None
        cursor.close()
        db.close()
    except mysql.connector.Error:
        found_items = []
        current_user_id = None
    return render_template('home.html', lost_items=[], found_items=found_items, active='found', current_user_id=current_user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            message = 'Please enter both username and password.'
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()
                cursor.close()
                db.close()

                if not user or not check_password_hash(user['password'], password):
                    message = 'Invalid username or password.'
                else:
                    session['username'] = username
                    return redirect(url_for('homepage'))

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('login.html', title='Login', message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip()
        contact_number   = request.form.get('contact_number', '').strip()
        location         = request.form.get('location', '').strip()
        password         = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not all([username, email, contact_number, location, password, confirm_password]):
            message = 'Please fill in all fields.'
        elif password != confirm_password:
            message = 'Passwords do not match.'
        else:
            try:
                db = get_db()
                cursor = db.cursor()
                cursor.execute(
                    'SELECT id FROM users WHERE username = %s OR email = %s',
                    (username, email)
                )
                existing = cursor.fetchone()

                if existing:
                    message = 'Username or email is already taken.'
                else:
                    hashed_pw = generate_password_hash(password)
                    cursor.execute(
                        'INSERT INTO users (username, password, email, contact_number, location) VALUES (%s, %s, %s, %s, %s)',
                        (username, hashed_pw, email, contact_number, location)
                    )
                    db.commit()
                    session['username'] = username
                    cursor.close()
                    db.close()
                    return redirect(url_for('homepage'))

                cursor.close()
                db.close()

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('register.html', title='Register', message=message)


@app.route('/report-lost', methods=['GET', 'POST'])
def report_lost():
    if not session.get('username'):
        return redirect(url_for('index'))

    message = None
    success = None

    if request.method == 'POST':
        item_type   = request.form.get('type', '').strip()
        details     = request.form.get('details', '').strip()
        location    = request.form.get('location', '').strip()

        if not all([item_type, details, location]):
            message = 'Please fill in all fields.'
        else:
            try:
                # Handle multiple photo uploads
                files = request.files.getlist('images')
                image_filenames = []
                for file in files:
                    if file and allowed_file(file.filename):
                        image_filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                        image_filenames.append(image_filename)

                db = get_db()
                cursor = db.cursor()

                cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
                user = cursor.fetchone()
                user_id = user[0] if user else None

                # Duplicate guard: same user, same type+location within 10 seconds
                cursor.execute(
                    '''SELECT id FROM lost_items WHERE user_id = %s AND type = %s AND location = %s
                       AND reported_at > NOW() - INTERVAL 10 SECOND''',
                    (user_id, item_type, location)
                )
                if cursor.fetchone():
                    cursor.close()
                    db.close()
                    success = 'Your lost item has been reported successfully!'
                else:
                    primary_image = image_filenames[0] if image_filenames else None
                    cursor.execute(
                        'INSERT INTO lost_items (user_id, type, details, location, image) VALUES (%s, %s, %s, %s, %s)',
                        (user_id, item_type, details, location, primary_image)
                    )
                    item_id = cursor.lastrowid

                    for fname in image_filenames:
                        cursor.execute(
                            'INSERT INTO item_photos (item_id, item_type, filename) VALUES (%s, %s, %s)',
                            (item_id, 'lost', fname)
                        )

                    db.commit()
                    cursor.close()
                    db.close()
                    success = 'Your lost item has been reported successfully!'

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('report_lost.html', message=message, success=success)



@app.route('/report-found', methods=['GET', 'POST'])
def report_found():
    if not session.get('username'):
        return redirect(url_for('index'))

    message = None
    success = None

    if request.method == 'POST':
        item_type   = request.form.get('type', '').strip()
        details     = request.form.get('details', '').strip()
        location    = request.form.get('location', '').strip()

        if not all([item_type, details, location]):
            message = 'Please fill in all fields.'
        else:
            try:
                # Handle multiple photo uploads
                files = request.files.getlist('images')
                image_filenames = []
                for file in files:
                    if file and allowed_file(file.filename):
                        image_filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                        image_filenames.append(image_filename)

                db = get_db()
                cursor = db.cursor()

                cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
                user = cursor.fetchone()
                user_id = user[0] if user else None

                primary_image = image_filenames[0] if image_filenames else None
                cursor.execute(
                    'INSERT INTO found_items (user_id, type, details, location, image) VALUES (%s, %s, %s, %s, %s)',
                    (user_id, item_type, details, location, primary_image)
                )
                item_id = cursor.lastrowid

                for fname in image_filenames:
                    cursor.execute(
                        'INSERT INTO item_photos (item_id, item_type, filename) VALUES (%s, %s, %s)',
                        (item_id, 'found', fname)
                    )

                db.commit()
                cursor.close()
                db.close()
                success = 'Your found item has been reported successfully!'

            except mysql.connector.Error as e:
                message = f'Database error: {e}'

    return render_template('report_found.html', message=message, success=success)


@app.route('/claim/<string:table>/<int:item_id>', methods=['POST'])
def claim_item(table, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('homepage'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get user id
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        user_id = user['id'] if user else None

        # Only update if this user owns the item
        cursor.execute(f'UPDATE {table} SET status = %s, claimed_at = NOW() WHERE id = %s AND user_id = %s', ('claimed', item_id, user_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('lost_page') if table == 'lost_items' else url_for('found_page'))


@app.route('/delete/<string:table>/<int:item_id>', methods=['POST'])
def delete_item(table, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('homepage'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get user id
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        user_id = user['id'] if user else None

        # Only delete if this user owns the item
        cursor.execute(f'UPDATE {table} SET status = %s WHERE id = %s AND user_id = %s', ('deleted', item_id, user_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('lost_page') if table == 'lost_items' else url_for('found_page'))


# =========================
# CHAT ROUTES
# =========================

@app.route('/chat/<string:item_type>/<int:item_id>')
def chat(item_type, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))
    if item_type not in ('lost', 'found'):
        return redirect(url_for('homepage'))

    table = 'lost_items' if item_type == 'lost' else 'found_items'

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get current user
        cursor.execute('SELECT id, username FROM users WHERE username = %s', (session['username'],))
        current_user = cursor.fetchone()

        # Get item + reporter info
        cursor.execute(f'''
            SELECT i.*, u.username AS reporter_name, u.id AS reporter_id
            FROM {table} i
            JOIN users u ON i.user_id = u.id
            WHERE i.id = %s
        ''', (item_id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            db.close()
            return redirect(url_for('homepage'))

        # Determine the other user (if reporter viewing, show all threads; if visitor, show their thread)
        is_reporter = current_user['id'] == item['reporter_id']

        if is_reporter:
            # Reporter sees list of all users who messaged about this item
            cursor.execute('''
                SELECT DISTINCT u.id, u.username
                FROM messages m
                JOIN users u ON (
                    CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END = u.id
                )
                WHERE m.item_id = %s AND m.item_type = %s
                AND (m.sender_id = %s OR m.receiver_id = %s)
            ''', (item['reporter_id'], item_id, item_type, item['reporter_id'], item['reporter_id']))
            threads = cursor.fetchall()

            # Get selected thread (from query param)
            from flask import request as freq
            selected_user_id = freq.args.get('with', type=int)

            messages = []
            other_user = None
            if selected_user_id:
                cursor.execute('SELECT id, username FROM users WHERE id = %s', (selected_user_id,))
                other_user = cursor.fetchone()
                cursor.execute('''
                    SELECT m.*, u.username AS sender_name
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.item_id = %s AND m.item_type = %s
                    AND ((m.sender_id = %s AND m.receiver_id = %s) OR (m.sender_id = %s AND m.receiver_id = %s))
                    ORDER BY m.sent_at ASC
                ''', (item_id, item_type, item['reporter_id'], selected_user_id, selected_user_id, item['reporter_id']))
                messages = cursor.fetchall()
                # Mark as read
                cursor.execute('''
                    UPDATE messages SET is_read = 1
                    WHERE item_id = %s AND item_type = %s AND sender_id = %s AND receiver_id = %s AND is_read = 0
                ''', (item_id, item_type, selected_user_id, item['reporter_id']))
                db.commit()
        else:
            threads = []
            other_user = {'id': item['reporter_id'], 'username': item['reporter_name']}
            cursor.execute('''
                SELECT m.*, u.username AS sender_name
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.item_id = %s AND m.item_type = %s
                AND ((m.sender_id = %s AND m.receiver_id = %s) OR (m.sender_id = %s AND m.receiver_id = %s))
                ORDER BY m.sent_at ASC
            ''', (item_id, item_type, current_user['id'], item['reporter_id'], item['reporter_id'], current_user['id']))
            messages = cursor.fetchall()
            # Mark as read
            cursor.execute('''
                UPDATE messages SET is_read = 1
                WHERE item_id = %s AND item_type = %s AND sender_id = %s AND receiver_id = %s AND is_read = 0
            ''', (item_id, item_type, item['reporter_id'], current_user['id']))
            db.commit()

        cursor.close()
        db.close()

        return render_template('chat.html',
            item=item,
            item_type=item_type,
            current_user=current_user,
            is_reporter=is_reporter,
            threads=threads,
            messages=messages,
            other_user=other_user
        )

    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/chat/<string:item_type>/<int:item_id>/send', methods=['POST'])
def send_message(item_type, item_id):
    if not session.get('username'):
        return redirect(url_for('index'))

    message_text = request.form.get('message', '').strip()
    receiver_id  = request.form.get('receiver_id', type=int)
    with_param   = request.form.get('with_user_id', type=int)

    if not receiver_id:
        return redirect(url_for('chat', item_type=item_type, item_id=item_id))

    # Handle photo upload
    image_filename = None
    message_type = 'text'
    file = request.files.get('chat_image')
    if file and allowed_file(file.filename):
        image_filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        message_type = 'image'
        if not message_text:
            message_text = ''

    if not message_text and not image_filename:
        if with_param:
            return redirect(url_for('chat', item_type=item_type, item_id=item_id) + f'?with={with_param}')
        return redirect(url_for('chat', item_type=item_type, item_id=item_id))

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        sender = cursor.fetchone()
        sender_id = sender['id']

        cursor.execute('''
            INSERT INTO messages (item_id, item_type, sender_id, receiver_id, message, image, message_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (item_id, item_type, sender_id, receiver_id, message_text, image_filename, message_type))
        db.commit()
        cursor.close()
        db.close()

    except mysql.connector.Error as e:
        pass

    if with_param:
        return redirect(url_for('chat', item_type=item_type, item_id=item_id) + f'?with={with_param}')
    return redirect(url_for('chat', item_type=item_type, item_id=item_id))


@app.route('/inbox')
def inbox():
    if not session.get('username'):
        return redirect(url_for('index'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get current user
        cursor.execute('SELECT id, username FROM users WHERE username = %s', (session['username'],))
        current_user = cursor.fetchone()

        # Get all unique conversations this user is involved in
        # (either as sender or receiver), grouped by item
        cursor.execute('''
            SELECT
                m.item_id,
                m.item_type,
                MAX(m.sent_at) AS last_message_time,
                MAX(m.message) AS last_message,
                SUM(CASE WHEN m.receiver_id = %s AND m.is_read = 0 THEN 1 ELSE 0 END) AS unread_count,
                CASE
                    WHEN m.sender_id = %s THEN m.receiver_id
                    ELSE m.sender_id
                END AS other_user_id
            FROM messages m
            WHERE m.sender_id = %s OR m.receiver_id = %s
            GROUP BY m.item_id, m.item_type, other_user_id
            ORDER BY last_message_time DESC
        ''', (current_user['id'], current_user['id'], current_user['id'], current_user['id']))
        raw_threads = cursor.fetchall()

        # Enrich each thread with item info and other user info
        threads = []
        for t in raw_threads:
            # Get other user info
            cursor.execute('SELECT id, username FROM users WHERE id = %s', (t['other_user_id'],))
            other_user = cursor.fetchone()

            # Get item info
            table = 'lost_items' if t['item_type'] == 'lost' else 'found_items'
            cursor.execute(f'SELECT id, type, image FROM {table} WHERE id = %s', (t['item_id'],))
            item = cursor.fetchone()

            if item and other_user:
                threads.append({
                    'item_id': t['item_id'],
                    'item_type': t['item_type'],
                    'item': item,
                    'other_user': other_user,
                    'last_message': t['last_message'],
                    'last_message_time': t['last_message_time'],
                    'unread_count': t['unread_count']
                })

        cursor.close()
        db.close()

        return render_template('inbox.html', threads=threads, current_user=current_user)

    except mysql.connector.Error as e:
        return f'Database error: {e}'


# =========================
# ADMIN ROUTES
# =========================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    message = None
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            message = 'Please enter both username and password.'
        else:
            try:
                db = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute('SELECT * FROM admin_users WHERE username = %s', (username,))
                admin = cursor.fetchone()
                cursor.close()
                db.close()
                if not admin or not check_password_hash(admin['password'], password):
                    message = 'Invalid admin credentials.'
                else:
                    session['admin_username'] = username
                    session['is_admin'] = True
                    return redirect(url_for('admin_dashboard'))
            except mysql.connector.Error as e:
                message = f'Database error: {e}'
    return render_template('admin_login.html', message=message)



@app.route('/admin/login-ajax', methods=['POST'])
def admin_login_ajax():
    from flask import jsonify
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': 'Please enter both fields.'})
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM admin_users WHERE username = %s', (username,))
        admin = cursor.fetchone()
        cursor.close()
        db.close()

        if not admin or not check_password_hash(admin['password'], password):
            return jsonify({'success': False, 'message': 'Invalid admin credentials.'})

        session['admin_username'] = username
        session['is_admin'] = True
        return jsonify({'success': True})

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # All lost items with reporter info
        cursor.execute('''
            SELECT i.*, u.username AS reporter_name
            FROM lost_items i
            LEFT JOIN users u ON i.user_id = u.id
            ORDER BY i.reported_at DESC
        ''')
        lost_items = cursor.fetchall()
        lost_items = attach_photos(cursor, lost_items, 'lost')

        # All found items with reporter info
        cursor.execute('''
            SELECT i.*, u.username AS reporter_name
            FROM found_items i
            LEFT JOIN users u ON i.user_id = u.id
            ORDER BY i.reported_at DESC
        ''')
        found_items = cursor.fetchall()
        found_items = attach_photos(cursor, found_items, 'found')

        # All users
        cursor.execute('SELECT id, username, email, contact_number, location, created_at FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()

        # Stats
        cursor.execute('SELECT COUNT(*) AS cnt FROM lost_items WHERE status = "active"')
        active_lost = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM found_items WHERE status = "active"')
        active_found = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM lost_items WHERE status = "claimed"')
        claimed_lost = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM found_items WHERE status = "claimed"')
        claimed_found = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM lost_items WHERE status = "deleted"')
        deleted_lost = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM found_items WHERE status = "deleted"')
        deleted_found = cursor.fetchone()['cnt']
        cursor.execute('SELECT COUNT(*) AS cnt FROM users')
        total_users = cursor.fetchone()['cnt']

        cursor.close()
        db.close()

        stats = {
            'active_lost': active_lost,
            'active_found': active_found,
            'claimed': claimed_lost + claimed_found,
            'deleted': deleted_lost + deleted_found,
            'total_users': total_users,
        }

        return render_template('admin_dashboard.html',
            lost_items=lost_items,
            found_items=found_items,
            users=users,
            stats=stats
        )
    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/admin/delete/<string:table>/<int:item_id>', methods=['POST'])
def admin_delete(table, item_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('admin_dashboard'))
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'UPDATE {table} SET status = %s WHERE id = %s', ('deleted', item_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/restore/<string:table>/<int:item_id>', methods=['POST'])
def admin_restore(table, item_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if table not in ('lost_items', 'found_items'):
        return redirect(url_for('admin_dashboard'))
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(f'UPDATE {table} SET status = %s WHERE id = %s', ('active', item_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('admin_dashboard'))


# =========================
# USER PROFILE ROUTES
# =========================

@app.route('/profile')
def profile():
    if not session.get('username'):
        return redirect(url_for('index'))
    return redirect(url_for('user_profile', username=session['username']))


@app.route('/profile/<username>')
def user_profile(username):
    if not session.get('username'):
        return redirect(url_for('index'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get user info
        cursor.execute('SELECT id, username, email, contact_number, location, created_at FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            db.close()
            return 'User not found', 404

        # Get their lost items (active + claimed, not deleted)
        cursor.execute('''
            SELECT * FROM lost_items
            WHERE user_id = %s AND status != "deleted"
            ORDER BY reported_at DESC
        ''', (user['id'],))
        lost_items = cursor.fetchall()
        lost_items = attach_photos(cursor, lost_items, 'lost')

        # Get their found items (active + claimed, not deleted)
        cursor.execute('''
            SELECT * FROM found_items
            WHERE user_id = %s AND status != "deleted"
            ORDER BY reported_at DESC
        ''', (user['id'],))
        found_items = cursor.fetchall()
        found_items = attach_photos(cursor, found_items, 'found')

        cursor.close()
        db.close()

        is_own_profile = session['username'] == username

        return render_template('profile.html',
            profile_user=user,
            lost_items=lost_items,
            found_items=found_items,
            is_own_profile=is_own_profile
        )
    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('username'):
        return redirect(url_for('index'))
    message = None
    success = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()

        if request.method == 'POST':
            email          = request.form.get('email', '').strip()
            contact_number = request.form.get('contact_number', '').strip()
            location       = request.form.get('location', '').strip()
            new_password   = request.form.get('new_password', '').strip()
            confirm_pw     = request.form.get('confirm_password', '').strip()

            if not all([email, contact_number, location]):
                message = 'Please fill in all fields.'
            elif new_password and new_password != confirm_pw:
                message = 'Passwords do not match.'
            else:
                if new_password:
                    hashed = generate_password_hash(new_password)
                    cursor.execute(
                        'UPDATE users SET email=%s, contact_number=%s, location=%s, password=%s WHERE username=%s',
                        (email, contact_number, location, hashed, session['username'])
                    )
                else:
                    cursor.execute(
                        'UPDATE users SET email=%s, contact_number=%s, location=%s WHERE username=%s',
                        (email, contact_number, location, session['username'])
                    )
                db.commit()
                success = 'Profile updated successfully!'
                # Refresh user data
                cursor.execute('SELECT * FROM users WHERE username = %s', (session['username'],))
                user = cursor.fetchone()

        cursor.close()
        db.close()
        return render_template('edit_profile.html', user=user, message=message, success=success)
    except mysql.connector.Error as e:
        return f'Database error: {e}'


# =========================
# SEARCH
# =========================

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('search.html', results=[], query='')
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        like = f'%{q}%'

        cursor.execute('''
            SELECT i.*, u.username AS reporter_name, 'lost' AS item_type
            FROM lost_items i
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.status = 'active' AND (i.type LIKE %s OR i.details LIKE %s OR i.location LIKE %s)
            ORDER BY i.reported_at DESC
        ''', (like, like, like))
        lost = cursor.fetchall()
        lost = attach_photos(cursor, lost, 'lost')

        cursor.execute('''
            SELECT i.*, u.username AS reporter_name, 'found' AS item_type
            FROM found_items i
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.status = 'active' AND (i.type LIKE %s OR i.details LIKE %s OR i.location LIKE %s)
            ORDER BY i.reported_at DESC
        ''', (like, like, like))
        found = cursor.fetchall()
        found = attach_photos(cursor, found, 'found')

        # Also search users
        cursor.execute('''
            SELECT id, username, location FROM users
            WHERE username LIKE %s OR location LIKE %s
        ''', (like, like))
        users = cursor.fetchall()

        cursor.close()
        db.close()
        results = lost + found
        return render_template('search.html', results=results, users=users, query=q)
    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/search/suggest')
def search_suggest():
    from flask import jsonify
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        like = f'%{q}%'
        suggestions = set()

        cursor.execute(
            "SELECT type FROM lost_items WHERE status='active' AND type LIKE %s LIMIT 5", (like,)
        )
        for r in cursor.fetchall(): suggestions.add(r['type'])

        cursor.execute(
            "SELECT type FROM found_items WHERE status='active' AND type LIKE %s LIMIT 5", (like,)
        )
        for r in cursor.fetchall(): suggestions.add(r['type'])

        cursor.execute(
            "SELECT location FROM lost_items WHERE status='active' AND location LIKE %s LIMIT 3", (like,)
        )
        for r in cursor.fetchall(): suggestions.add(r['location'])

        cursor.execute(
            "SELECT username FROM users WHERE username LIKE %s LIMIT 3", (like,)
        )
        for r in cursor.fetchall(): suggestions.add(r['username'])

        cursor.close()
        db.close()
        return jsonify(sorted(list(suggestions))[:8])
    except mysql.connector.Error as e:
        return jsonify([])


# =========================
# REPORT/FLAG POSTS
# =========================

@app.route('/report-post', methods=['POST'])
def report_post():
    from flask import jsonify
    if not session.get('username'):
        return jsonify({'success': False, 'message': 'Please log in first.'})

    item_id   = request.form.get('item_id', type=int)
    item_type = request.form.get('item_type', '')
    reason    = request.form.get('reason', '').strip()
    details   = request.form.get('details', '').strip()

    if not all([item_id, item_type, reason]):
        return jsonify({'success': False, 'message': 'Please fill in all fields.'})

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT id FROM users WHERE username = %s', (session['username'],))
        user = cursor.fetchone()
        reporter_id = user['id'] if user else None

        cursor.execute(
            'INSERT INTO reports (reporter_id, item_id, item_type, reason, details) VALUES (%s, %s, %s, %s, %s)',
            (reporter_id, item_id, item_type, reason, details)
        )
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Report submitted. Thank you!'})
    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


# Update admin dashboard to include reports

@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # --- STAT CARDS ---
        cursor.execute("SELECT COUNT(*) AS cnt FROM lost_items WHERE status='active'")
        active_lost = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM found_items WHERE status='active'")
        active_found = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM lost_items WHERE status='claimed'")
        claimed_lost = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM found_items WHERE status='claimed'")
        claimed_found = cursor.fetchone()['cnt']
        total_items = active_lost + active_found + claimed_lost + claimed_found
        total_claimed = claimed_lost + claimed_found
        recovery_rate = round((total_claimed / total_items * 100) if total_items > 0 else 0, 1)

        cursor.execute("SELECT COUNT(*) AS cnt FROM users")
        total_users = cursor.fetchone()['cnt']

        # Avg claim time in hours
        cursor.execute("""
            SELECT AVG(TIMESTAMPDIFF(HOUR, reported_at, claimed_at)) AS avg_h
            FROM lost_items WHERE claimed_at IS NOT NULL
        """)
        r = cursor.fetchone()
        avg_lost = r['avg_h'] or 0
        cursor.execute("""
            SELECT AVG(TIMESTAMPDIFF(HOUR, reported_at, claimed_at)) AS avg_h
            FROM found_items WHERE claimed_at IS NOT NULL
        """)
        r = cursor.fetchone()
        avg_found = r['avg_h'] or 0
        avg_claim_hours = round((avg_lost + avg_found) / 2) if (avg_lost or avg_found) else 0

        # --- LINE CHART: lost vs found last 8 weeks ---
        cursor.execute("""
            SELECT DATE_FORMAT(reported_at, '%Y-%u') AS wk, COUNT(*) AS cnt
            FROM lost_items GROUP BY wk ORDER BY wk DESC LIMIT 8
        """)
        lost_weekly = {r['wk']: r['cnt'] for r in cursor.fetchall()}
        cursor.execute("""
            SELECT DATE_FORMAT(reported_at, '%Y-%u') AS wk, COUNT(*) AS cnt
            FROM found_items GROUP BY wk ORDER BY wk DESC LIMIT 8
        """)
        found_weekly = {r['wk']: r['cnt'] for r in cursor.fetchall()}
        all_weeks = sorted(set(list(lost_weekly.keys()) + list(found_weekly.keys())))[-8:]
        weekly_labels = all_weeks
        weekly_lost   = [lost_weekly.get(w, 0) for w in all_weeks]
        weekly_found  = [found_weekly.get(w, 0) for w in all_weeks]

        # --- DONUT: status breakdown ---
        cursor.execute("SELECT COUNT(*) AS cnt FROM lost_items WHERE status='deleted'")
        del_lost = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM found_items WHERE status='deleted'")
        del_found = cursor.fetchone()['cnt']
        donut_data = [active_lost + active_found, total_claimed, del_lost + del_found]

        # --- BAR: top item types ---
        cursor.execute("""
            SELECT type, COUNT(*) AS cnt FROM lost_items GROUP BY type
            UNION ALL
            SELECT type, COUNT(*) AS cnt FROM found_items GROUP BY type
            ORDER BY cnt DESC LIMIT 8
        """)
        type_rows = cursor.fetchall()
        type_labels = [r['type'] for r in type_rows]
        type_counts = [r['cnt'] for r in type_rows]

        # --- BAR: top locations ---
        cursor.execute("""
            SELECT location, COUNT(*) AS cnt FROM lost_items GROUP BY location
            UNION ALL
            SELECT location, COUNT(*) AS cnt FROM found_items GROUP BY location
            ORDER BY cnt DESC LIMIT 8
        """)
        loc_rows = cursor.fetchall()
        loc_labels = [r['location'] for r in loc_rows]
        loc_counts = [r['cnt'] for r in loc_rows]

        # --- LINE: user growth last 8 months ---
        cursor.execute("""
            SELECT DATE_FORMAT(created_at, '%Y-%m') AS mo, COUNT(*) AS cnt
            FROM users GROUP BY mo ORDER BY mo DESC LIMIT 8
        """)
        growth_rows = cursor.fetchall()
        growth_labels = [r['mo'] for r in reversed(growth_rows)]
        growth_counts = [r['cnt'] for r in reversed(growth_rows)]

        # --- TABLE: most active users ---
        cursor.execute("""
            SELECT u.username,
                COUNT(DISTINCT l.id) AS lost_count,
                COUNT(DISTINCT f.id) AS found_count
            FROM users u
            LEFT JOIN lost_items l ON l.user_id = u.id
            LEFT JOIN found_items f ON f.user_id = u.id
            GROUP BY u.id
            ORDER BY (COUNT(DISTINCT l.id) + COUNT(DISTINCT f.id)) DESC
            LIMIT 5
        """)
        top_users = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template('admin_analytics.html',
            recovery_rate=recovery_rate,
            total_items=total_items,
            total_users=total_users,
            avg_claim_hours=avg_claim_hours,
            weekly_labels=weekly_labels,
            weekly_lost=weekly_lost,
            weekly_found=weekly_found,
            donut_data=donut_data,
            type_labels=type_labels,
            type_counts=type_counts,
            loc_labels=loc_labels,
            loc_counts=loc_counts,
            growth_labels=growth_labels,
            growth_counts=growth_counts,
            top_users=top_users,
        )
    except mysql.connector.Error as e:
        return f'Database error: {e}'

@app.route('/admin/reports')
def admin_reports():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('''
            SELECT r.*, u.username AS reporter_name
            FROM reports r
            LEFT JOIN users u ON r.reporter_id = u.id
            ORDER BY r.created_at DESC
        ''')
        reports = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('admin_reports.html', reports=reports)
    except mysql.connector.Error as e:
        return f'Database error: {e}'


@app.route('/admin/reports/<int:report_id>/<string:action>', methods=['POST'])
def admin_report_action(report_id, action):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if action not in ('reviewed', 'dismissed'):
        return redirect(url_for('admin_reports'))
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE reports SET status = %s WHERE id = %s', (action, report_id))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error:
        pass
    return redirect(url_for('admin_reports'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(debug=True)