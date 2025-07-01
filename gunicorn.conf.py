# Gunicorn configuration for Medical Transcription App
# Optimized for handling large audio file uploads and processing

import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
backlog = 2048

# Worker processes
workers = 1  # Single worker to avoid memory issues with large files
worker_class = "sync"
worker_connections = 1000
timeout = 600  # 10 minutes - enough for large audio file processing
keepalive = 2

# Restart workers after this many requests, to help with memory leaks
max_requests = 100
max_requests_jitter = 10

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "medical-transcription-app"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (not used in this deployment)
keyfile = None
certfile = None

# Memory and file limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Preload app for better memory usage
preload_app = True

# Worker timeout specifically for long-running requests
graceful_timeout = 30
worker_tmp_dir = "/dev/shm"  # Use memory for temporary files when possible

