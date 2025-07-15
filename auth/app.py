import os
import sqlite3
import hashlib
import secrets
import jwt
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, session, render_template_string, redirect
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'medical_auth.db')

# Main app URL for redirect
MAIN_APP_URL = 'https://medical-transcription-app-bkm3.onrender.com'

def init_db():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                consent_given BOOLEAN DEFAULT 0,
                consent_date TIMESTAMP
            )
        ''')
        
        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def hash_password(password, salt=None):
    """Hash password using PBKDF2 with SHA-256"""
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Use PBKDF2 with 100,000 iterations
    password_hash = hashlib.pbkdf2_hmac('sha256', 
                                       password.encode('utf-8'), 
                                       salt.encode('utf-8'), 
                                       100000)
    return password_hash.hex(), salt

def verify_password(password, stored_hash, salt):
    """Verify password against stored hash"""
    password_hash, _ = hash_password(password, salt)
    return password_hash == stored_hash

def generate_jwt_token(user_data):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'email': user_data['email'],
        'first_name': user_data['first_name'],
        'last_name': user_data['last_name'],
        'exp': datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
        'iat': datetime.utcnow()
    }
    
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

def log_audit(user_id, action, details=None, ip_address=None, user_agent=None):
    """Log user actions for compliance"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (user_id, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, ip_address, user_agent))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit logging error: {e}")

# HTML Template with redirect functionality
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medical Authentication Platform</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            width: 100%;
            max-width: 450px;
            text-align: center;
        }

        .logo {
            font-size: 48px;
            margin-bottom: 10px;
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }

        .tabs {
            display: flex;
            margin-bottom: 30px;
            border-radius: 10px;
            overflow: hidden;
            background: #f5f5f5;
        }

        .tab {
            flex: 1;
            padding: 15px;
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .tab.active {
            background: #667eea;
            color: white;
        }

        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }

        input[type="text"], input[type="email"], input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e1e1;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }

        .checkbox-group {
            display: flex;
            align-items: flex-start;
            margin-bottom: 20px;
            text-align: left;
        }

        .checkbox-group input[type="checkbox"] {
            margin-right: 10px;
            margin-top: 2px;
        }

        .checkbox-group label {
            margin-bottom: 0;
            font-size: 14px;
            line-height: 1.4;
        }

        .btn {
            width: 100%;
            padding: 15px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s ease;
        }

        .btn:hover {
            background: #5a6fd8;
        }

        .logout-btn {
            background: #dc3545;
        }

        .logout-btn:hover {
            background: #c82333;
        }

        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 8px;
            font-weight: 500;
        }

        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .hidden {
            display: none !important;
        }

        .dashboard {
            text-align: center;
        }

        .welcome-message {
            font-size: 24px;
            color: #333;
            margin-bottom: 30px;
            font-weight: 600;
        }

        .user-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }

        .user-info h3 {
            color: #333;
            margin-bottom: 10px;
        }

        .user-info p {
            color: #666;
            font-size: 16px;
        }

        .redirect-message {
            background: #e3f2fd;
            border: 1px solid #90caf9;
            color: #1565c0;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .redirect-message h3 {
            margin-bottom: 10px;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🏥</div>
        <h1>Medical Platform</h1>
        <p class="subtitle">Secure Authentication System</p>
        
        <div id="alerts"></div>
        
        <!-- Authentication Section -->
        <div id="auth-section">
            <div class="tabs">
                <button class="tab active" onclick="showTab('login')">Login</button>
                <button class="tab" onclick="showTab('register')">Register</button>
            </div>
            
            <!-- Login Tab -->
            <div id="login-tab">
                <form id="login-form">
                    <div class="form-group">
                        <label for="login-username">Username</label>
                        <input type="text" id="login-username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="login-password">Password</label>
                        <input type="password" id="login-password" name="password" required>
                    </div>
                    <button type="submit" class="btn">Login</button>
                </form>
            </div>
            
            <!-- Register Tab -->
            <div id="register-tab" class="hidden">
                <form id="register-form">
                    <div class="form-group">
                        <label for="register-username">Username</label>
                        <input type="text" id="register-username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="register-email">Email</label>
                        <input type="email" id="register-email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="register-first-name">First Name</label>
                        <input type="text" id="register-first-name" name="first_name" required>
                    </div>
                    <div class="form-group">
                        <label for="register-last-name">Last Name</label>
                        <input type="text" id="register-last-name" name="last_name" required>
                    </div>
                    <div class="form-group">
                        <label for="register-password">Password</label>
                        <input type="password" id="register-password" name="password" required>
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="consent" name="consent_given" required>
                        <label for="consent">I consent to the processing of my personal data in accordance with GDPR</label>
                    </div>
                    <button type="submit" class="btn">Register</button>
                </form>
            </div>
        </div>
        
        <!-- Redirect Section -->
        <div id="redirect-section" class="hidden">
            <div class="redirect-message">
                <h3>Login Successful!</h3>
                <p>Redirecting you to the Medical Transcription App...</p>
                <div class="spinner"></div>
                <p><small>If you are not redirected automatically, <a href="#" id="manual-redirect">click here</a>.</small></p>
            </div>
        </div>
    </div>

    <script>
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('[id$="-tab"]').forEach(t => t.classList.add('hidden'));
            
            document.querySelector(`button[onclick="showTab('${tab}')"]`).classList.add('active');
            document.getElementById(tab + '-tab').classList.remove('hidden');
        }

        function showAlert(message, type) {
            const alertsDiv = document.getElementById('alerts');
            const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
            alertsDiv.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
            
            setTimeout(() => {
                alertsDiv.innerHTML = '';
            }, 5000);
        }

        function redirectToMainApp(token, userData) {
            // Show redirect message
            document.getElementById('auth-section').classList.add('hidden');
            document.getElementById('redirect-section').classList.remove('hidden');
            
            // Construct redirect URL with authentication data
            const redirectUrl = `${MAIN_APP_URL}?token=${encodeURIComponent(token)}&user=${encodeURIComponent(userData.username)}&name=${encodeURIComponent(userData.first_name + ' ' + userData.last_name)}`;
            
            // Set up manual redirect link
            document.getElementById('manual-redirect').href = redirectUrl;
            
            // Redirect after 3 seconds
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 3000);
        }

        async function login() {
            const form = document.getElementById('login-form');
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: formData.get('username'),
                        password: formData.get('password')
                    }),
                    credentials: 'include'
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Redirect to main app with token
                    redirectToMainApp(data.token, data.user);
                } else {
                    showAlert(data.message, 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        async function register() {
            const form = document.getElementById('register-form');
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: formData.get('username'),
                        email: formData.get('email'),
                        first_name: formData.get('first_name'),
                        last_name: formData.get('last_name'),
                        password: formData.get('password'),
                        consent_given: formData.get('consent_given') === 'on'
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert(data.message + ' Please login.', 'success');
                    showTab('login');
                    form.reset();
                } else {
                    showAlert(data.message, 'error');
                }
            } catch (error) {
                showAlert('Network error. Please try again.', 'error');
            }
        }

        // Form event listeners
        document.getElementById('login-form').addEventListener('submit', function(e) {
            e.preventDefault();
            login();
        });

        document.getElementById('register-form').addEventListener('submit', function(e) {
            e.preventDefault();
            register();
        });

        // Set main app URL for JavaScript
        const MAIN_APP_URL = '{{ main_app_url }}';
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template_string(HTML_TEMPLATE, main_app_url=MAIN_APP_URL)

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'first_name', 'last_name', 'password', 'consent_given']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Validate consent
        if not data.get('consent_given'):
            return jsonify({'message': 'GDPR consent is required'}), 400
        
        # Hash password
        password_hash, salt = hash_password(data['password'])
        
        # Insert user into database
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (username, email, first_name, last_name, password_hash, salt, consent_given, consent_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['username'],
                data['email'],
                data['first_name'],
                data['last_name'],
                password_hash,
                salt,
                1,
                datetime.now(timezone.utc).isoformat()
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Log registration
            log_audit(user_id, 'USER_REGISTERED', 
                     f"User {data['username']} registered", 
                     request.remote_addr, 
                     request.headers.get('User-Agent'))
            
            return jsonify({'message': 'Registration successful'}), 201
            
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return jsonify({'message': 'Username already exists'}), 409
            elif 'email' in str(e):
                return jsonify({'message': 'Email already exists'}), 409
            else:
                return jsonify({'message': 'Registration failed'}), 409
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user login and return JWT token"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Username and password required'}), 400
        
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, first_name, last_name, password_hash, salt, is_active
            FROM users WHERE username = ?
        ''', (data['username'],))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401
        
        user_id, username, email, first_name, last_name, stored_hash, salt, is_active = user
        
        if not is_active:
            return jsonify({'message': 'Account is disabled'}), 401
        
        if not verify_password(data['password'], stored_hash, salt):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # Create session
        session['user_id'] = user_id
        session['username'] = username
        
        # Update last login
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                      (datetime.now(timezone.utc).isoformat(), user_id))
        conn.commit()
        conn.close()
        
        # Generate JWT token
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name
        }
        
        token = generate_jwt_token(user_data)
        
        # Log login
        log_audit(user_id, 'USER_LOGIN', 
                 f"User {username} logged in", 
                 request.remote_addr, 
                 request.headers.get('User-Agent'))
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user_data
        }), 200
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/verify', methods=['POST'])
def verify_token():
    """Verify JWT token"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'message': 'Token required'}), 400
        
        try:
            payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            return jsonify({
                'valid': True,
                'user': {
                    'id': payload['user_id'],
                    'username': payload['username'],
                    'email': payload['email'],
                    'first_name': payload['first_name'],
                    'last_name': payload['last_name']
                }
            }), 200
        except jwt.ExpiredSignatureError:
            return jsonify({'valid': False, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'valid': False, 'message': 'Invalid token'}), 401
            
    except Exception as e:
        print(f"Token verification error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        if user_id:
            log_audit(user_id, 'USER_LOGOUT', 
                     f"User {username} logged out", 
                     request.remote_addr, 
                     request.headers.get('User-Agent'))
        
        session.clear()
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/profile', methods=['GET'])
def profile():
    """Get user profile"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'message': 'Not authenticated'}), 401
        
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, first_name, last_name, created_at, last_login
            FROM users WHERE id = ? AND is_active = 1
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            session.clear()
            return jsonify({'message': 'User not found'}), 404
        
        user_id, username, email, first_name, last_name, created_at, last_login = user
        
        return jsonify({
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'created_at': created_at,
                'last_login': last_login
            }
        }), 200
        
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}), 200

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

