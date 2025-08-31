# Enhanced Medical Dictation App v2.0 - Deployment Guide

## 🚀 New Features Implemented

### 1. **Claude Opus Medical Validation** 🤖
- Integrated Claude Opus API for sophisticated medical reasoning
- Advanced validation of medical logic, terminology, and safety
- Comprehensive Dutch medical standards compliance checking
- API Key: `your_claude_api_key_here`

### 2. **Intelligent Self-Correction Orchestrator** 🔄
- Automatic iterative verification and correction behind the scenes
- Up to 5 iterations of self-improvement per report
- Multi-agent verification system with hallucination detection
- Confidence scoring and quality metrics

### 3. **Patient ID OCR System** 📷
- Automatic extraction of patient ID and DOB from wristband/card photos
- Advanced image preprocessing and OCR with Tesseract
- Support for Dutch medical ID formats
- Intelligent validation and error correction

### 4. **Background Processing** ⚡
- Celery + Redis for asynchronous processing
- Real-time job status tracking
- Automatic cleanup of old jobs
- Health monitoring and periodic tasks

### 5. **Enhanced Audio Recording** 🎤
- WebM format support with automatic fallback
- Auto-download of recordings
- Session storage for recovery
- Improved audio quality settings

### 6. **Comprehensive Review Interface** 📝
- Side-by-side transcript and report editing
- Real-time Claude Opus validation
- Version history and auto-save
- Export functionality with confidence scores

## 📋 Prerequisites

### System Requirements
- Python 3.11+
- Redis server
- Tesseract OCR with Dutch language support
- OpenAI API access
- Claude Opus API access

### API Keys Required
- **OpenAI API Key**: Set as `OPENAI_API_KEY` environment variable
- **Claude API Key**: Already integrated in code

## 🛠️ Installation Steps

### 1. Clone and Setup
```bash
git clone https://github.com/jdverbek/dictation-app-v2
cd dictation-app-v2
```

### 2. Install Dependencies
```bash
# Install Python packages
pip3 install -r requirements.txt

# Install system packages
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-nld redis-server
```

### 3. Configure Environment
```bash
# Set environment variables
export OPENAI_API_KEY="your_openai_api_key"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your_secret_key"
```

### 4. Start Services
```bash
# Use the provided startup script
./start_services.sh
```

Or manually:
```bash
# Start Redis
redis-server --daemonize yes

# Start Celery worker
cd src
celery -A core.background_tasks.celery_app worker --loglevel=info --detach

# Start Celery beat
celery -A core.background_tasks.celery_app beat --loglevel=info --detach

# Start Flask app
python3 app.py
```

## 🌐 Deployment Options

### Option 1: Render Deployment (Recommended)
1. **Update your existing Render service**:
   - Connect to your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `cd src && gunicorn app:app --bind 0.0.0.0:$PORT`

2. **Add Redis Add-on**:
   - In Render dashboard, add Redis add-on
   - Set `REDIS_URL` environment variable

3. **Set Environment Variables**:
   ```
   OPENAI_API_KEY=your_openai_api_key
   REDIS_URL=your_redis_url_from_addon
   SECRET_KEY=your_secret_key
   ```

### Option 2: Local Development
```bash
# Start all services
./start_services.sh

# Access at http://localhost:5000
```

### Option 3: Docker Deployment
```dockerfile
# Dockerfile (create this)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-nld \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["./start_services.sh"]
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key

# Optional
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=medical_app.db
FLASK_ENV=production
```

### Redis Configuration
- Default: `localhost:6379`
- For production: Use managed Redis service
- Memory: At least 512MB recommended

### File Storage
- Audio files: `uploads/audio/`
- Temporary images: `uploads/temp/`
- Ensure write permissions

## 📊 Monitoring and Health Checks

### Health Check Endpoint
```
GET /api/health
```

Returns:
```json
{
  "status": "healthy",
  "services": {
    "redis": "connected",
    "openai": "available",
    "claude": "available"
  }
}
```

### Job Status Tracking
```
GET /api/job/status/{job_id}
```

### Celery Monitoring
```bash
# Check worker status
celery -A core.background_tasks.celery_app inspect active

# Check scheduled tasks
celery -A core.background_tasks.celery_app inspect scheduled
```

## 🔒 Security Features

### OWASP Compliance
- ✅ Content Security Policy (CSP)
- ✅ Strict Transport Security (HSTS)
- ✅ X-Frame-Options protection
- ✅ XSS Protection
- ✅ Rate limiting
- ✅ Input validation and sanitization
- ✅ Secure session management
- ✅ GDPR compliance

### Security Headers
All responses include comprehensive security headers for maximum protection.

## 🎯 Usage Flow

### 1. Patient Information
- Enter patient ID manually OR
- Upload photo of wristband/card for automatic OCR extraction

### 2. Audio Recording
- **Option A**: Record directly in browser with enhanced WebM support
- **Option B**: Upload existing audio file

### 3. Background Processing
- Automatic transcription with Whisper
- Iterative verification and self-correction
- Claude Opus medical validation
- Real-time status updates

### 4. Review and Edit
- Comprehensive review interface
- Side-by-side transcript and report view
- Real-time Claude validation
- Version history and auto-save
- Export functionality

## 🔍 API Endpoints

### Core Processing
- `POST /api/process` - Process audio recording
- `GET /api/job/status/{job_id}` - Get job status
- `GET /review/{job_id}` - Review interface

### Patient OCR
- `POST /api/extract-patient-id` - Extract patient info from image

### Report Management
- `POST /api/job/{job_id}/save` - Save edited report
- `POST /api/job/{job_id}/autosave` - Auto-save report
- `POST /api/job/{job_id}/validate` - Validate with Claude
- `GET /api/job/{job_id}/versions` - Get version history

### System
- `GET /api/health` - Health check

## 🚨 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Restart Redis
   redis-server --daemonize yes
   ```

2. **Celery Worker Not Starting**
   ```bash
   # Check worker status
   ps aux | grep celery
   
   # Restart workers
   pkill -f celery
   cd src && celery -A core.background_tasks.celery_app worker --loglevel=info --detach
   ```

3. **OCR Not Working**
   ```bash
   # Install Tesseract
   sudo apt-get install tesseract-ocr tesseract-ocr-nld
   
   # Test OCR
   tesseract --version
   ```

4. **Claude API Errors**
   - Verify API key is correct
   - Check rate limits
   - Monitor API usage

### Logs
- Application logs: Console output
- Security audit: `security_audit.log`
- Celery logs: Worker console output

## 📈 Performance Optimization

### Recommended Settings
- **Workers**: 2-4 Celery workers per CPU core
- **Redis Memory**: 512MB minimum, 2GB recommended
- **File Storage**: SSD recommended for audio processing
- **Network**: Stable connection for API calls

### Scaling
- Horizontal scaling: Multiple worker instances
- Vertical scaling: Increase memory and CPU
- Database: Consider PostgreSQL for production

## 🔄 Maintenance

### Regular Tasks
- Monitor disk space for audio files
- Check Redis memory usage
- Review security audit logs
- Update dependencies regularly

### Backup
- Database: Regular SQLite backups
- Redis: Periodic snapshots
- Audio files: Archive old recordings

## 📞 Support

For issues or questions:
1. Check logs for error details
2. Verify all services are running
3. Test API endpoints individually
4. Review configuration settings

---

**Enhanced Medical Dictation App v2.0**  
*Powered by Claude Opus, OpenAI Whisper, and advanced medical AI*

