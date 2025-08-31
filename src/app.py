import io
import os
import datetime
import openai
import sqlite3
import hashlib
import secrets
import time
import logging
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash
from openai import OpenAI

# Import enhanced API
from api.enhanced_api import enhanced_api

app = Flask(__name__)

# Register enhanced API blueprint
app.register_blueprint(enhanced_api)

# Configure session with secure settings
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=2)  # Session timeout

# Security configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Configure logging for security audit
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_audit.log'),
        logging.StreamHandler()
    ]
)
security_logger = logging.getLogger('security_audit')

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    # Content Security Policy - Prevent XSS attacks
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # Strict Transport Security - Force HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # XSS Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy - Allow camera for barcode scanning
    response.headers['Permissions-Policy'] = (
        "camera=(self), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )
    
    # Remove server information
    response.headers.pop('Server', None)
    
    return response

def rate_limit(max_requests=10, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            current_time = time.time()
            
            # Clean old entries
            rate_limit_storage[client_ip] = [
                timestamp for timestamp in rate_limit_storage.get(client_ip, [])
                if current_time - timestamp < window
            ]
            
            # Check rate limit
            if len(rate_limit_storage.get(client_ip, [])) >= max_requests:
                security_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Add current request
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = []
            rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, user_id=None, details=None):
    """Log security-related events for audit trail"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    security_logger.info(f"SECURITY_EVENT: {event_type} | "
                        f"User: {user_id} | "
                        f"IP: {client_ip} | "
                        f"UserAgent: {user_agent} | "
                        f"Details: {details}")

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'medical_app.db')

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
        
        # Create transcription_history table for user's previous outputs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcription_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                patient_id TEXT,
                verslag_type TEXT NOT NULL,
                original_transcript TEXT,
                structured_report TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Add patient_id column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE transcription_history ADD COLUMN patient_id TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

def hash_password(password, salt=None):
    """Hash password with salt using SHA-256"""
    if salt is None:
        salt = secrets.token_hex(32)
    
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

def verify_password(password, stored_hash, salt):
    """Verify password against stored hash"""
    password_hash, _ = hash_password(password, salt)
    return password_hash == stored_hash

def create_user(username, email, first_name, last_name, password, consent_given=True):
    """Create a new user in the database"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            conn.close()
            return False, "Username or email already exists"
        
        # Hash password
        password_hash, salt = hash_password(password)
        
        # Insert user
        cursor.execute('''
            INSERT INTO users (username, email, first_name, last_name, password_hash, salt, consent_given, consent_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, first_name, last_name, password_hash, salt, consent_given, datetime.datetime.now()))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return True, user_id
    except Exception as e:
        return False, str(e)

def authenticate_user(username, password):
    """Authenticate user and return user data"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, first_name, last_name, password_hash, salt, is_active
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return False, "Invalid credentials"
        
        user_id, username, email, first_name, last_name, stored_hash, salt, is_active = user
        
        if not is_active:
            return False, "Account is disabled"
        
        if verify_password(password, stored_hash, salt):
            # Update last login
            conn = sqlite3.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.datetime.now(), user_id))
            conn.commit()
            conn.close()
            
            return True, {
                'id': user_id,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}"
            }
        else:
            return False, "Invalid credentials"
    except Exception as e:
        return False, str(e)

def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current user data from session"""
    if 'user_id' in session:
        return {
            'id': session['user_id'],
            'username': session['username'],
            'email': session['email'],
            'first_name': session['first_name'],
            'last_name': session['last_name'],
            'full_name': session['full_name']
        }
    return None

def save_transcription(user_id, verslag_type, original_transcript, structured_report, patient_id=None):
    """Save transcription to user's history"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transcription_history (user_id, patient_id, verslag_type, original_transcript, structured_report)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, patient_id, verslag_type, original_transcript, structured_report))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving transcription: {e}")
        return False

def get_user_transcription_history(user_id, limit=50):
    """Get user's transcription history"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, patient_id, verslag_type, original_transcript, structured_report, created_at
            FROM transcription_history 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'patient_id': row[1] or 'Niet opgegeven',
                'verslag_type': row[2],
                'original_transcript': row[3],
                'structured_report': row[4],
                'created_at': row[5]
            })
        
        return history
    except Exception as e:
        print(f"Error getting transcription history: {e}")
        return []

# Initialize database on startup
init_db()

def call_gpt(messages, model="gpt-4o", temperature=0.0):
    """Call GPT with error handling"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def quality_control_review(structured_report, original_transcript):
    """Perform quality control review of the structured report"""
    
    review_instruction = """
Je bent een ervaren cardioloog die een tweede review doet van een TTE-verslag. 
Controleer het verslag op de volgende punten:

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE (PRIORITEIT!):
- Corrigeer ALLE incorrecte samengestelde woorden:
  ❌ 'pulmonaardruk' → ✅ 'pulmonale druk'
  ❌ 'posteriorklepplat' → ✅ 'posterieur mitraalklepblad'
  ❌ 'tricuspiedklep' → ✅ 'tricuspidalisklep'
  ❌ 'mitraalsklep' → ✅ 'mitralisklep'
  ❌ 'aortaklep' → ✅ 'aortaklep'
- Gebruik ALTIJD correcte medische Nederlandse terminologie

MEDISCHE CONSISTENTIE:
- Zijn de metingen medisch logisch? (bijv. LVEF vs functie beschrijving)
- Zijn er tegenstrijdigheden tussen verschillende secties?
- Kloppen de verhoudingen tussen verschillende parameters?

TEMPLATE VOLLEDIGHEID:
- Zijn alle verplichte secties aanwezig?
- Is de formatting correct en consistent?
- Zijn er lege velden die ingevuld zouden moeten zijn?

LOGISCHE COHERENTIE:
- Klopt de conclusie met de bevindingen?
- Is het beleid logisch gebaseerd op de bevindingen?
- Zijn er missing links tussen bevindingen en conclusies?

MEDISCHE VEILIGHEID:
- Zijn er potentieel gevaarlijke inconsistenties?
- Zijn kritieke bevindingen correct weergegeven?
- Is de terminologie correct gebruikt?

Als je fouten of inconsistenties vindt, corrigeer ze en geef het verbeterde verslag terug.
Als alles correct is, geef het originele verslag terug zonder wijzigingen.

BELANGRIJK: 
- Behoud de exacte template structuur
- Voeg GEEN nieuwe medische gegevens toe die niet in het origineel stonden
- Corrigeer alleen echte fouten en inconsistenties
- CORRIGEER ALTIJD incorrecte terminologie naar correcte medische Nederlandse termen
- Geef ALLEEN het gecorrigeerde verslag terug, geen uitleg

Origineel dictaat voor referentie:
{original_transcript}

Te reviewen verslag:
{structured_report}

Gecorrigeerd verslag:
"""
    
    try:
        reviewed_report = call_gpt([
            {"role": "system", "content": review_instruction.format(
                original_transcript=original_transcript,
                structured_report=structured_report
            )},
            {"role": "user", "content": "Voer de quality control review uit."}
        ])
        
        return reviewed_report.strip()
    except Exception as e:
        # If review fails, return original report
        return structured_report

def detect_hallucination(structured_report, transcript):
    """Detect potential hallucination in the structured report"""
    
    import re
    
    # Extract numbers from the structured report and transcript
    numbers_in_report = re.findall(r'\d+(?:\.\d+)?', structured_report)
    numbers_in_transcript = re.findall(r'\d+(?:\.\d+)?', transcript)
    
    # Convert to sets for better comparison
    report_numbers = set(numbers_in_report)
    transcript_numbers = set(numbers_in_transcript)
    
    # Count fabricated numbers (in report but not in transcript)
    fabricated_numbers = len(report_numbers - transcript_numbers)
    total_numbers = len(report_numbers)
    
    # More sophisticated hallucination detection
    if total_numbers > 0:
        fabrication_ratio = fabricated_numbers / total_numbers
        
        # Only flag as hallucination if:
        # 1. High fabrication ratio (>70%) AND significant number of fabricated numbers (>5)
        # 2. OR extremely high fabrication ratio (>90%) with any fabricated numbers
        if (fabrication_ratio > 0.7 and fabricated_numbers > 5) or (fabrication_ratio > 0.9 and fabricated_numbers > 2):
            return True, f"Mogelijk hallucinatie gedetecteerd: {fabricated_numbers}/{total_numbers} cijfers niet in origineel dictaat (ratio: {fabrication_ratio:.1%})"
    
    # Check for suspiciously repetitive patterns (classic hallucination sign)
    lines = structured_report.split('\n')
    repetitive_patterns = 0
    for line in lines:
        # Look for repetitive phrases or identical measurements across different structures
        if 'normaal' in line.lower() and len(re.findall(r'normaal', line.lower())) > 2:
            repetitive_patterns += 1
    
    if repetitive_patterns > 5:
        return True, "Mogelijk hallucinatie: verdacht repetitieve patronen gedetecteerd"
    
    # Check for impossible medical combinations
    if "LVEF 65%" in structured_report and "ernstig gedaalde functie" in structured_report:
        return True, "Mogelijk hallucinatie: tegenstrijdige medische bevindingen"
    
    # If transcript is very short but report is very detailed, might be hallucination
    transcript_words = len(transcript.split())
    report_words = len(structured_report.split())
    
    if transcript_words < 20 and report_words > 200 and total_numbers > 10:
        return True, f"Mogelijk hallucinatie: zeer kort dictaat ({transcript_words} woorden) maar uitgebreid verslag ({report_words} woorden)"
    
    return False, None

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window=300)  # 5 attempts per 5 minutes
def login():
    """Login route with security logging"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Input validation
        if not username or not password:
            log_security_event('LOGIN_ATTEMPT_FAILED', details='Missing credentials')
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        # Sanitize username input
        if len(username) > 50 or any(char in username for char in ['<', '>', '"', "'"]):
            log_security_event('LOGIN_ATTEMPT_SUSPICIOUS', details=f'Invalid username format: {username[:20]}')
            flash('Invalid username format', 'error')
            return render_template('login.html')
        
        success, result = authenticate_user(username, password)
        
        if success:
            # Store user data in session
            session['user_id'] = result['id']
            session['username'] = result['username']
            session['email'] = result['email']
            session['first_name'] = result['first_name']
            session['last_name'] = result['last_name']
            session['full_name'] = result['full_name']
            session.permanent = True  # Enable session timeout
            
            log_security_event('LOGIN_SUCCESS', user_id=result['id'], details=f'User: {username}')
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            log_security_event('LOGIN_ATTEMPT_FAILED', details=f'Failed login for username: {username}')
            flash(result, 'error')
            return render_template('login.html')
    
    # If user is already logged in, redirect to main app
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@rate_limit(max_requests=3, window=300)  # 3 attempts per 5 minutes
def register():
    """Register route with security logging"""
    if request.method == 'POST':
        # Get and sanitize form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        gdpr_consent = request.form.get('consent_given') == 'on'
        
        # Input validation
        if not all([username, email, first_name, last_name, password]):
            log_security_event('REGISTRATION_ATTEMPT_FAILED', details='Missing required fields')
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        # Validate input lengths and characters
        if (len(username) > 50 or len(email) > 100 or 
            len(first_name) > 50 or len(last_name) > 50):
            log_security_event('REGISTRATION_ATTEMPT_SUSPICIOUS', details='Field length exceeded')
            flash('Input fields too long', 'error')
            return render_template('register.html')
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
        for field in [username, email, first_name, last_name]:
            if any(char in field.lower() for char in suspicious_chars):
                log_security_event('REGISTRATION_ATTEMPT_SUSPICIOUS', 
                                 details=f'Suspicious characters in input: {field[:20]}')
                flash('Invalid characters in input fields', 'error')
                return render_template('register.html')
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            log_security_event('REGISTRATION_ATTEMPT_FAILED', details=f'Invalid email format: {email}')
            flash('Invalid email format', 'error')
            return render_template('register.html')
        
        # Password strength validation
        if len(password) < 8:
            log_security_event('REGISTRATION_ATTEMPT_FAILED', details='Weak password')
            flash('Password must be at least 8 characters long', 'error')
            return render_template('register.html')
        
        if not gdpr_consent:
            log_security_event('REGISTRATION_ATTEMPT_FAILED', details='GDPR consent not given')
            flash('You must agree to the GDPR terms to register', 'error')
            return render_template('register.html')
        
        success, result = create_user(username, email, first_name, last_name, password)
        
        if success:
            log_security_event('REGISTRATION_SUCCESS', details=f'New user: {username}, Email: {email}')
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            log_security_event('REGISTRATION_ATTEMPT_FAILED', details=f'Registration failed: {result}')
            flash(result, 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout route with security logging"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    if user_id:
        log_security_event('LOGOUT_SUCCESS', user_id=user_id, details=f'User: {username}')
    
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/prior-reports')
@login_required
def prior_reports():
    """View user's prior transcription reports"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    history = get_user_transcription_history(user['id'])
    return render_template('prior_reports.html', user=user, history=history)

# SEO and Security Routes
@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt file"""
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml file"""
    return app.send_static_file('sitemap.xml')

@app.route('/')
@login_required
def index():
    user = get_current_user()
    return render_template('enhanced_index.html', user=user)

@app.route('/classic')
@login_required
def classic_index():
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/transcribe', methods=['POST'])
@login_required
@rate_limit(max_requests=20, window=300)  # 20 transcriptions per 5 minutes
def transcribe():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    try:
        # Get and validate form data
        verslag_type = request.form.get('verslag_type', 'TTE')
        patient_id = request.form.get('patient_id', '').strip()
        disable_hallucination = request.form.get('disable_hallucination_detection') == 'true'
        
        # Validate verslag_type
        allowed_types = ['TTE', 'TEE', 'Anamnese', 'Stress echo', 'Holter', 'Pacemaker controle']
        if verslag_type not in allowed_types:
            log_security_event('TRANSCRIBE_ATTEMPT_SUSPICIOUS', user_id=user['id'], 
                             details=f'Invalid verslag_type: {verslag_type}')
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Validate patient_id
        if patient_id:
            if len(patient_id) > 50 or any(char in patient_id for char in ['<', '>', '"', "'"]):
                log_security_event('TRANSCRIBE_ATTEMPT_SUSPICIOUS', user_id=user['id'], 
                                 details=f'Invalid patient_id format: {patient_id[:20]}')
                return jsonify({'error': 'Invalid patient ID format'}), 400
        
        # Handle file upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file.filename != '':
                # Validate file size and type
                if audio_file.content_length and audio_file.content_length > 50 * 1024 * 1024:  # 50MB
                    log_security_event('TRANSCRIBE_ATTEMPT_FAILED', user_id=user['id'], 
                                     details='File too large')
                    return jsonify({'error': 'File too large (max 50MB)'}), 400
                
                # Log transcription attempt
                log_security_event('TRANSCRIBE_ATTEMPT', user_id=user['id'], 
                                 details=f'Type: {verslag_type}, Patient: {patient_id or "None"}')
                
                # Process audio file with Whisper
                if verslag_type == 'Anamnese':
                    prompt = "Dit is een conversatie tussen een arts en een patiënt in het West-Vlaams dialect. Transcribeer de volledige conversatie."
                else:
                    prompt = "Dit is een medische dictatie in het Nederlands van een cardioloog. Transcribeer de volledige dictatie."
                
                try:
                    # Convert FileStorage to the format expected by OpenAI
                    audio_file.seek(0)  # Reset file pointer to beginning
                    
                    # Debug: Check file info
                    file_content = audio_file.read()
                    audio_file.seek(0)  # Reset again
                    
                    print(f"DEBUG: File size: {len(file_content)} bytes")
                    print(f"DEBUG: File name: {audio_file.filename}")
                    print(f"DEBUG: Content type: {audio_file.content_type}")
                    print(f"DEBUG: First 20 bytes: {file_content[:20]}")
                    
                    # Check if file is actually WebM (common issue with browser recordings)
                    if file_content.startswith(b'\x1a\x45\xdf\xa3'):
                        print("DEBUG: File is WebM format, adjusting content type")
                        content_type = 'audio/webm'
                        filename = audio_file.filename.replace('.wav', '.webm')
                    else:
                        content_type = audio_file.content_type
                        filename = audio_file.filename
                    
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(filename, file_content, content_type),
                        temperature=0.0
                    )
                    corrected_transcript = transcript.text
                    
                    # Debug: Check if transcription is empty or too short
                    if not corrected_transcript or len(corrected_transcript.strip()) < 10:
                        return render_template('index.html', 
                                             error=f"⚠️ Transcriptie probleem: Audio werd niet correct getranscribeerd.\n\nBestand info:\n- Grootte: {len(file_content)} bytes\n- Type: {content_type}\n- Resultaat: '{corrected_transcript}'\n\nProbeer opnieuw met een duidelijkere opname of schakel hallucinatiedetectie uit.",
                                             verslag_type=verslag_type)
                    
                    # Check for Whisper hallucination (repetitive prompt text)
                    if "transcribe" in corrected_transcript.lower() or "dictatie" in corrected_transcript.lower():
                        # Count how many times the prompt appears
                        prompt_count = corrected_transcript.lower().count("transcribe") + corrected_transcript.lower().count("dictatie")
                        if prompt_count > 5:  # If prompt appears more than 5 times, it's likely hallucination
                            return render_template('index.html', 
                                                 error=f"🚨 Whisper Hallucinatie Gedetecteerd!\n\nHet audio bestand is te stil of onduidelijk. Whisper herhaalt de instructie in plaats van te transcriberen:\n\n'{corrected_transcript[:200]}...'\n\nOplossingen:\n- Spreek dichterbij de microfoon\n- Verhoog het volume\n- Verminder achtergrondgeluid\n- Spreek langzamer en duidelijker\n\nProbeer opnieuw met een betere opname.",
                                                 verslag_type=verslag_type)
                    
                    # Debug: Show transcription length for troubleshooting
                    print(f"DEBUG: Transcription length: {len(corrected_transcript)} characters")
                    print(f"DEBUG: Transcription preview: {corrected_transcript[:200]}...")
                    
                except Exception as e:
                    print(f"DEBUG: Transcription error: {str(e)}")
                    return render_template('index.html', error=f"Transcriptie fout: {str(e)}\n\nBestand info:\n- Naam: {audio_file.filename}\n- Type: {audio_file.content_type}\n- Grootte: {len(audio_file.read()) if audio_file else 'onbekend'} bytes")
            else:
                return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")
        else:
            return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")

        # Get today's date
        today = datetime.datetime.now().strftime("%d-%m-%Y")
        
        # Generate report based on type
        if verslag_type == 'TTE':
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een cardioloog. Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

KRITIEKE VEILIGHEIDSREGEL: VERZIN GEEN MEDISCHE GEGEVENS!

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden zoals 'pulmonaardruk' → gebruik 'pulmonale druk'
- GEEN 'posteriorklepplat' → gebruik 'posterieur mitraalklepblad'
- GEEN 'tricuspiedklep' → gebruik 'tricuspidalisklep'
- GEEN 'mitraalsklep' → gebruik 'mitralisklep'
- GEEN 'aortaklep' → gebruik 'aortaklep'

CORRECTE TERMINOLOGIE VOORBEELDEN:
❌ FOUT: pulmonaardruk, posteriorklepplat, tricuspiedklep
✅ CORRECT: pulmonale druk, posterieur mitraalklepblad, tricuspidalisklep

Uw taak: Analyseer het dictaat en vul het TTE-template in met ALLEEN de WERKELIJK GENOEMDE BEVINDINGEN.

TEMPLATE STRUCTUUR REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: geef een medische beschrijving gebaseerd op wat genoemd is
- Voor specifieke parameters (cijfers): alleen invullen als expliciet genoemd
- Voor algemene beschrijvingen: gebruik logische medische termen
- GEBRUIK ALTIJD CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE

INVUL REGELS:
1. EXPLICIET GENOEMDE AFWIJKINGEN: Vul exact in zoals gedicteerd MAAR met correcte terminologie
2. NIET GENOEMDE STRUCTUREN: Gebruik "normaal" of "eutroof" 
3. SPECIFIEKE CIJFERS: Alleen als letterlijk genoemd (EDD, LVEF, etc.)
4. ALGEMENE FUNCTIE: Afleiden uit context ("normale echo" = goede functie)
5. TERMINOLOGIE: Altijd correcte medische Nederlandse termen gebruiken

VOORBEELDEN VAN CORRECTE INVULLING:

Als "normale echo behalve..." gedicteerd:
- Linker ventrikel: eutroof, globale functie goed
- Regionaal: geen kinetiekstoornissen  
- Rechter ventrikel: normaal, globale functie goed

Als specifieke afwijking genoemd:
- Mitralisklep: morfologisch prolaps. insufficiëntie: spoortje
- Atria: LA licht vergroot 51 mm

Als niets specifiek genoemd:
- Aortaklep: tricuspied, morfologisch normaal. Functioneel: normaal
- Pericard: normaal

VOLLEDIGE TEMPLATE STRUCTUUR:

TTE op {today}:
- Linker ventrikel: [normaal/eutroof als niet anders vermeld, specifieke afwijkingen als genoemd]
- Regionaal: [geen kinetiekstoornissen als niet anders vermeld]
- Rechter ventrikel: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Diastole: [normaal als niet anders vermeld, specifieke bevindingen als genoemd]
- Atria: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Aortadimensies: [normaal als niet anders vermeld, specifieke metingen als genoemd]
- Mitralisklep: [morfologisch normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Aortaklep: [tricuspied, morfologisch normaal als niet anders vermeld]
- Pulmonalisklep: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Tricuspidalisklep: [normaal als niet anders vermeld, specifieke afwijkingen als genoemd]
- Pericard: [normaal als niet anders vermeld]

Recente biochemie op {today}:
[Alleen invullen als biochemie expliciet genoemd in dictaat]

Conclusie: [Samenvatting van werkelijk genoemde afwijkingen]

Beleid:
[Alleen invullen als expliciet genoemd in dictaat]

VEILIGHEIDSCHECK: Elk cijfer moet ECHT in het dictaat staan!
TERMINOLOGIE CHECK: Gebruik ALLEEN correcte medische Nederlandse termen!
"""
        elif verslag_type == 'TEE':
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een TEE (transesofageale echocardiografie). Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

KRITIEKE VEILIGHEIDSREGEL: VERZIN GEEN MEDISCHE GEGEVENS!

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden
- Correcte anatomische benamingen voor TEE structuren

Uw taak: Analyseer het dictaat en vul het TEE-template in met ALLEEN de WERKELIJK GENOEMDE BEVINDINGEN.

TEMPLATE STRUCTUUR REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: geef een medische beschrijving gebaseerd op wat genoemd is
- Voor specifieke parameters (cijfers): alleen invullen als expliciet genoemd
- Voor algemene beschrijvingen: gebruik logische medische termen
- GEBRUIK ALTIJD CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE

INVUL REGELS:
1. EXPLICIET GENOEMDE AFWIJKINGEN: Vul exact in zoals gedicteerd MAAR met correcte terminologie
2. NIET GENOEMDE STRUCTUREN: Gebruik "normaal" of "geen afwijkingen"
3. SPECIFIEKE CIJFERS: Alleen als letterlijk genoemd
4. ALGEMENE FUNCTIE: Afleiden uit context
5. TERMINOLOGIE: Altijd correcte medische Nederlandse termen gebruiken

VOLLEDIGE TEE TEMPLATE STRUCTUUR:

Onderzoeksdatum: {today}
Bevindingen: TEE ONDERZOEK : 3D TEE met [toestel als genoemd, anders "niet vermeld"] toestel
Indicatie: [alleen invullen als expliciet genoemd in dictaat]
Afname mondeling consent: dr. Verbeke. Informed consent: patiënt kreeg uitleg over aard onderzoek, mogelijke resultaten en procedurele risico's en verklaart zich hiermee akkoord.
Supervisie: dr [alleen invullen als genoemd]
Verpleegkundige: [alleen invullen als genoemd]
Anesthesist: dr. [alleen invullen als genoemd]
Locatie: [alleen invullen als genoemd]
Sedatie met [alleen invullen als genoemd] en topicale Xylocaine spray.
[Vlotte/moeizame] introductie TEE probe, [Vlot/moeizaam] verloop van onderzoek zonder complicatie.

VERSLAG:
- Linker ventrikel is [eutroof/hypertroof als genoemd], [niet/mild/matig/ernstig] gedilateerd en [normocontractiel/licht hypocontractiel/matig hypocontractiel/ernstig hypocontractiel] [zonder/met] regionale wandbewegingstoornissen.
- Rechter ventrikel is [eutroof/hypertroof als genoemd], [niet/mild/matig/ernstig] gedilateerd en [normocontractiel/licht hypocontractiel/matig hypocontractiel/ernstig hypocontractiel].
- De atria zijn [niet/licht/matig/sterk] gedilateerd.
- Linker hartoortje is [niet/wel] vergroot, er is [geen/beperkt] spontaan contrast, zonder toegevoegde structuur. Hartoortje snelheden [alleen cijfer als genoemd] cm/s.
- Interatriaal septum [is intact met kleurendoppler en na contrasttoediening met Valsalva manoever/is intact met kleurendoppler maar zonder contrast/vertoont een PFO/vertoont een ASD].
- Mitralisklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], er is [geen/lichte/matige/ernstige] insufficiëntie, er is [geen/lichte/matige/ernstige] stenose, [zonder/met] toegevoegde structuur.
* Mitraalinsufficientie vena contracta [alleen als genoemd] mm, ERO [alleen als genoemd] mm2 en RVol [alleen als genoemd] ml/slag.
- Aortaklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], [niet/mild/matig/ernstig] verkalkt, er is [geen/lichte/matige/ernstige] insufficiëntie, er is [geen/lichte/matige/ernstige] stenose [zonder/met] toegevoegde structuur.
Dimensies: LVOT [alleen als genoemd] mm, aorta sinus [alleen als genoemd] mm, sinutubulaire junctie [alleen als genoemd] mm, aorta ascendens boven de sinutubulaire junctie [alleen als genoemd] mm.
* Aortaklepinsufficientie vena contracta [alleen als genoemd] mm, ERO [alleen als genoemd] mm2 en RVol [alleen als genoemd] ml/slag.
* Aortaklepstenose piekgradient [alleen als genoemd] mmHg en gemiddelde gradient [alleen als genoemd] mmHg, effectief klepoppervlak [alleen als genoemd] cm2.
- Tricuspidalisklep: [natieve klep/bioprothese/mechanische kunstklep], morfologisch [normaal/degeneratief/prolaps], er is [geen/lichte/matige/ernstige] insufficiëntie, [zonder/met] toegevoegde structuur.
* Systolische pulmonale druk afgeleid uit TI [alleen als genoemd] mmHg + CVD.
- Pulmonalisklep is [normaal/sclerotisch], er is [geen/lichte/matige/ernstige] insufficiëntie.
- Aorta ascendens is [niet/mild/matig/aneurysmatisch] gedilateerd, graad [I/II/III/IV/V] atheromatose van de aortawand.
- Pulmonale arterie is [niet/mild/matig/aneurysmatisch] gedilateerd.
- Vena cava inferior/levervenes zijn [niet/mild/matig/ernstig] verbreed [met/zonder] ademvariatie.
- Pericard: er is [geen/mild/matig/uitgesproken] pericardvocht.

VEILIGHEIDSCHECK: Elk cijfer moet ECHT in het dictaat staan!
TERMINOLOGIE CHECK: Gebruik ALLEEN correcte medische Nederlandse termen!
"""
        elif verslag_type in ['Spoedconsult', 'Raadpleging', 'Consult']:
            # Template for spoedconsult, raadpleging, consult with user's exact template structure
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een cardioloog. Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

KRITIEKE ANTI-HALLUCINATIE REGEL: VERZIN ABSOLUUT GEEN MEDISCHE GEGEVENS!

STRIKT STRAMIEN REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: vul ALLEEN in wat EXPLICIET genoemd is
- Voor niet-genoemde informatie: laat de (...) staan of gebruik standaard waarden waar aangegeven
- GEEN gissingen, GEEN aannames, GEEN logische afleidingen
- VEILIGHEID EERST: beter (...) dan verzonnen data

CORRECTE MEDISCHE NEDERLANDSE TERMINOLOGIE:
- Gebruik ALTIJD correcte medische Nederlandse termen
- GEEN samengestelde woorden

VOLLEDIGE TEMPLATE STRUCTUUR (EXACT VOLGEN):

Reden van komst: [alleen invullen als expliciet genoemd, anders leeglaten]
Voorgeschiedenis: [alleen invullen als expliciet genoemd, anders leeglaten]
Persoonlijke antecedenten: [alleen invullen als expliciet genoemd, anders leeglaten]
Familiaal
- prematuur coronair lijden: [alleen invullen als expliciet genoemd, anders leeglaten]
- plotse dood: [alleen invullen als expliciet genoemd, anders leeglaten]
Beroep: [alleen invullen als expliciet genoemd, anders leeglaten]
Usus:
- nicotine: [alleen invullen als expliciet genoemd, anders leeglaten]
- ethyl: [alleen invullen als expliciet genoemd, anders leeglaten]
- druggebruik: [alleen invullen als expliciet genoemd, anders leeglaten]
Anamnese
Retrosternale last: [alleen invullen als expliciet genoemd, anders leeglaten]
Dyspneu: [alleen invullen als expliciet genoemd, anders leeglaten]
Palpitaties: [alleen invullen als expliciet genoemd, anders leeglaten]
Zwelling onderste ledematen: [alleen invullen als expliciet genoemd, anders leeglaten]
Draaierigheid/syncope: [alleen invullen als expliciet genoemd, anders leeglaten]
Lichamelijk onderzoek
Cor: [als niet genoemd: "regelmatig, geen souffle."]
Longen: [als niet genoemd: "zuiver."]
Perifeer: [als niet genoemd: "geen oedemen."]
Jugulairen: [als niet genoemd: "niet gestuwd."]
Aanvullend onderzoek
ECG op raadpleging ({today}):
- ritme: [kies uit: sinusaal/VKF/voorkamerflutter/atriale tachycardie of (...) als niet genoemd]
- PR: [kies uit: normaal/verlengd/verkort + (...) ms of (...) als niet genoemd]
- QRS: [kies uit: normale/linker/rechter as, smal/verbreed met LBTB/verbreed met RBTB/verbreed met aspecifiek IVCD of (...) als niet genoemd]
- repolarisatie: [kies uit: normaal/gestoord met... of (...) als niet genoemd]
- QTc: [kies uit: normaal/verlengd + (...) ms of (...) als niet genoemd]
Fietsproef op raadpleging ({today}):
[Als genoemd: "Patiënt fietst tot (...) W waarbij de hartslag oploopt van (...) tot (...)/min ((...)% van de voor leeftijd voorspelde waarde). De bloeddruk stijgt tot (...)/(...)mmHg. Klachten: (ja/neen). ECG tijdens inspanning toont (wel/geen) argumenten voor ischemie en (wel/geen) aritmie." - vul alleen bekende waarden in]
[Als niet genoemd: leeglaten]
TTE op raadpleging ({today}):
Linker ventrikel: [als genoemd: "(...)troof met EDD (...) mm, IVS (...) mm, PW (...) mm. Globale functie: (goed/licht gedaald/matig gedaald/ernstig gedaald) met LVEF (...)% (geschat/monoplane/biplane)." - vul alleen bekende waarden in]
Regionaal: [als genoemd: kies uit "geen kinetiekstoornissen/zone van hypokinesie/zone van akinesie"]
Rechter ventrikel: [als genoemd: "(...)troof, globale functie: (...) met TAPSE (...) mm." - vul alleen bekende waarden in]
Diastole: [als genoemd: kies uit "normaal/vertraagde relaxatie/dysfunctie graad 2/dysfunctie graad 3" + "met E (...) cm/s, A (...) cm/s, E DT (...) ms, E' septaal (...) cm/s, E/E' (...). L-golf: (ja/neen)." - vul alleen bekende waarden in]
Atria: [als genoemd: "LA (normaal/licht gedilateerd/sterk gedilateerd) (...) mm." - vul alleen bekende waarden in]
Aortadimensies: [als genoemd: "(normaal/gedilateerd) met sinus (...) mm, sinotubulair (...) mm, ascendens (...) mm." - vul alleen bekende waarden in]
Mitralisklep: [als genoemd: "morfologisch (normaal/sclerotisch/verdikt/prolaps/restrictief). insufficiëntie: (...), stenose: geen." - vul alleen bekende waarden in]
Aortaklep: [als genoemd: "(tricuspied/bicuspied), morfologisch (normaal/sclerotisch/mild verkalkt/matig verkalkt/ernstig verkalkt). Functioneel: insufficiëntie: geen, stenose: geen." - vul alleen bekende waarden in]
Pulmonalisklep: [als genoemd: "insufficiëntie: spoor, stenose: geen." of vul bekende waarden in]
Tricuspidalisklep: [als genoemd: "insufficiëntie: (...), geschatte RVSP: (...mmHg/niet opmeetbaar) + CVD (...) mmHg gezien vena cava inferior: (...) mm, variabiliteit: (...)." - vul alleen bekende waarden in]
Pericard: [als genoemd: vul in, anders "(...)."]
Recente biochemie op datum ({today}):
- Hb: [als genoemd: "(...) g/dL", anders "(...) g/dL"]
- Creatinine: [als genoemd: "(...) mg/dL en eGFR (...) mL/min.", anders "(...) mg/dL en eGFR (...) mL/min."]
- LDL: [als genoemd: "(...) mg/dL", anders "(...) mg/dL"]
- HbA1c: [als genoemd: "(...)%", anders "(...)%"]
Besluit
[Als genoemd: vul in, anders gebruik standaard structuur:]
Uw (...)-jarige patiënt werd gezien op de raadpleging cardiologie op {today}. Wij weerhouden volgende problematiek:
1. [Probleem 1 + beschrijving + aanpak als genoemd]
2. [Probleem 2 + beschrijving + aanpak als genoemd]
...
Verder: aandacht dient te gaan naar optimale cardiovasculaire preventie met:
- Vermijden van tabak.
- Tensiecontrole( met streefdoel <130/80 mmHg/. Geen gekende hypertensie). Graag uw verdere opvolging.
- LDL-cholesterol < (100/70/55) mg/dL. Actuele waarde (...) mg/dL (aldus goed onder controle/waarvoor opstart /waarvoor intensifiëring van de statinetherapie naar ).
- (Adequate glycemiecontrole met streefdoel HbA1c <6.5%/Geen argumenten voor diabetes mellitus type II).
- Lichaamsgewicht: BMI 20-25 kg/m² na te streven.
- Lifestyle-advies: mediterraan dieet arm aan verzadigde of dierlijke vetten en focus op volle graan producten, groente, fruit en vis. Zoveel lichaamsbeweging als mogelijk met liefst dagelijks beweging en 3-5x/week ged. 30 min een matige fysieke inspanning.

VEILIGHEIDSCHECK: Elk gegeven moet ECHT in het dictaat staan!
ANTI-HALLUCINATIE: Bij twijfel altijd (...) gebruiken!
"""
        elif verslag_type == 'Vrij dictaat':
            template_instruction = f"""
U krijgt een medische dictatie in het Nederlands. Uw taak is om hiervan een professioneel, coherent medisch verslag te maken ZONDER gebruik van een vaste template.

BELANGRIJKE REGELS:
1. GEEN TEMPLATE GEBRUIKEN - maak een vrij, professioneel verslag
2. INCORPOREER ALLE INFORMATIE uit de dictatie
3. CORRIGEER ZELFCORRECTIES - als de spreker zichzelf later corrigeert, gebruik de laatste/correcte versie
4. HERSCHRIJF VOOR COHERENTIE - maak een logische, vloeiende tekst
5. BEHOUD MEDISCHE PRECISIE - alle medische termen en waarden exact overnemen
6. PROFESSIONELE STIJL - geschikt voor medisch dossier

STRUCTUUR RICHTLIJNEN:
- Begin met context (datum, type onderzoek, patiënt info indien genoemd)
- Organiseer informatie logisch (anamnese → onderzoek → bevindingen → conclusie)
- Gebruik professionele medische taal
- Maak duidelijke paragrafen voor verschillende onderwerpen
- Eindig met conclusie en/of aanbevelingen indien van toepassing

VOORBEELD AANPAK:
Als de dictatie bevat: "Patiënt komt voor... eh nee wacht, eigenlijk voor controle na... ja dat klopt, controle na myocardinfarct"
Dan schrijf je: "Patiënt komt voor controle na myocardinfarct"

Maak een professioneel, samenhangend medisch verslag van de volgende dictatie:
"""
        else:
            # Default fallback for unknown report types
            template_instruction = f"""
U krijgt een medische dictatie in het Nederlands. Maak hiervan een professioneel medisch verslag.

BELANGRIJKE REGELS:
1. VERZIN GEEN MEDISCHE GEGEVENS
2. Gebruik alleen informatie die expliciet genoemd is
3. Gebruik correcte medische Nederlandse terminologie
4. Maak een logisch gestructureerd verslag

Maak een professioneel medisch verslag van de volgende dictatie:
"""

        # Generate structured report
        print(f"DEBUG: About to call GPT with transcript length: {len(corrected_transcript)}")
        print(f"DEBUG: Template instruction length: {len(template_instruction)}")
        
        structured = call_gpt([
            {"role": "system", "content": template_instruction},
            {"role": "user", "content": f"Transcriptie van het dictaat:\n\n{corrected_transcript}"}
        ])
        
        print(f"DEBUG: GPT response length: {len(structured)}")
        print(f"DEBUG: GPT response preview: {structured[:200]}...")
        
        # Check if GPT is giving a generic "can't transcribe" response
        if "kan de volledige dictatie niet transcriberen" in structured.lower() or "specifieke inhoud" in structured.lower():
            return render_template('index.html', 
                                 error=f"🚨 GPT Probleem: Het systeem kon het dictaat niet verwerken. \n\nOriginele transcriptie ({len(corrected_transcript)} karakters):\n{corrected_transcript}\n\nProbeer opnieuw of schakel hallucinatiedetectie uit.",
                                 verslag_type=verslag_type)
        
        # Clean the output to ensure only the template format is returned
        if "Verslag:" in structured:
            structured = structured.split("Verslag:")[-1].strip()
        
        # Remove any processing details that might appear before the template
        lines = structured.split('\n')
        template_start = -1
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if (line_stripped.startswith('TTE op') or 
                line_stripped.startswith('TEE op') or 
                line_stripped.startswith('Spoedconsult') or
                line_stripped.startswith('Reden van komst:') or
                line_stripped.startswith('Voorgeschiedenis:') or
                'Onderzoeksdatum:' in line_stripped):
                template_start = i
                break
        
        if template_start >= 0:
            structured = '\n'.join(lines[template_start:])

        # Perform quality control review (only if we have substantial content)
        if len(corrected_transcript.strip()) > 50:  # Only do QC if we have substantial content
            try:
                print(f"DEBUG: Performing quality control review")
                reviewed = quality_control_review(structured, corrected_transcript)
                if reviewed and len(reviewed.strip()) > 50 and "geen specifieke" not in reviewed.lower():
                    structured = reviewed
                    print(f"DEBUG: Quality control completed successfully")
                else:
                    print(f"DEBUG: Quality control failed or returned generic response, using original")
            except Exception as e:
                print(f"DEBUG: Quality control error: {str(e)}, using original structured report")
        else:
            print(f"DEBUG: Skipping quality control due to minimal transcription content ({len(corrected_transcript)} chars)")
            
        # Additional check: if structured report looks like a generic "can't process" message
        if len(structured.strip()) < 100 or "geen specifieke" in structured.lower() or "niet verstrekt" in structured.lower():
            return render_template('index.html', 
                                 error=f"⚠️ Verwerking probleem: Het systeem kon geen bruikbaar verslag genereren.\n\nOriginele transcriptie ({len(corrected_transcript)} karakters):\n{corrected_transcript}\n\nMogelijke oorzaken:\n- Audio kwaliteit te laag\n- Dictaat te kort of onduidelijk\n- Technische problemen\n\nProbeer opnieuw met een duidelijkere opname of schakel hallucinatiedetectie uit.",
                                 verslag_type=verslag_type)

        # Check for hallucination (only if not disabled)
        if not disable_hallucination:
            is_hallucination, hallucination_msg = detect_hallucination(structured, corrected_transcript)
            
            if is_hallucination:
                # If hallucination detected, show warning and original transcript
                error_msg = f"🚨 Mogelijk hallucinatie gedetecteerd!\n\n{hallucination_msg}\n\nHet systeem heeft mogelijk medische gegevens verzonnen die niet in het originele dictaat stonden. Controleer het originele dictaat hieronder en probeer opnieuw met een duidelijker opname.\n\nOrigineel dictaat:\n{corrected_transcript}"
                return render_template('index.html', 
                                     error=error_msg,
                                     verslag_type=verslag_type)

        # Save transcription to user's history
        user = get_current_user()
        if user:
            save_transcription(user['id'], verslag_type, corrected_transcript, structured, patient_id)

        return render_template('index.html', 
                             transcript=corrected_transcript,
                             structured=structured,
                             verslag_type=verslag_type,
                             user=user)

    except Exception as e:
        return render_template('index.html', error=f"Er is een fout opgetreden: {str(e)}")

@app.route('/verbeter', methods=['POST'])
@login_required
def verbeter():
    """Improve and clean up a medical report by removing unfilled items professionally"""
    try:
        data = request.get_json()
        verslag = data.get('verslag', '')
        verslag_type = data.get('verslag_type', '')
        
        if not verslag:
            return jsonify({'success': False, 'error': 'Geen verslag ontvangen'})
        
        # Create improvement instruction
        improvement_instruction = """
U krijgt een medisch verslag dat mogelijk incomplete secties bevat (met (...) of lege velden). 
Uw taak is om dit verslag professioneel op te schonen door:

VERBETERING REGELS:
1. VERWIJDER incomplete secties die alleen (...) bevatten
2. BEHOUD alle secties met echte medische informatie
3. HERFORMULEER zinnen om lege plekken elegant weg te werken
4. BEHOUD de professionele medische structuur
5. ZORG voor vloeiende overgangen tussen secties
6. GEEN nieuwe medische informatie toevoegen

VOORBEELDEN VAN VERBETERING:

VOOR: "Mitralisklep: morfologisch (...). insufficiëntie: (...), stenose: geen."
NA: "Mitralisklep: geen significante stenose."

VOOR: "- Hb: (...) g/dL\n- Creatinine: (...) mg/dL"  
NA: [Hele biochemie sectie weglaten als alles (...) is]

VOOR: "Cor: regelmatig, geen souffle.\nLongen: (...)\nPerifeer: geen oedemen."
NA: "Cor: regelmatig, geen souffle. Perifeer: geen oedemen."

Het resultaat moet een professioneel, leesbaar medisch verslag zijn zonder incomplete secties.

Verbeter het volgende verslag:
"""
        
        # Call GPT to improve the report
        verbeterd = call_gpt([
            {"role": "system", "content": improvement_instruction},
            {"role": "user", "content": verslag}
        ])
        
        return jsonify({'success': True, 'verbeterd_verslag': verbeterd})
        
    except Exception as e:
        print(f"Error in verbeter: {e}")
        return jsonify({'success': False, 'error': str(e)})
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

