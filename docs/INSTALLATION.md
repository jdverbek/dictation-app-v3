# 📖 Installation Guide

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Git (for cloning the repository)

## Quick Installation

### 1. Clone the Repository
```bash
git clone <your-github-repo-url>
cd jdverbek-dictation-app
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
nano .env  # or use your preferred editor
```

**Required environment variables:**
```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
# Development mode
python src/app.py

# Production mode with Gunicorn
gunicorn --bind 0.0.0.0:10000 src.app:app
```

### 5. Access the Application
Open your browser and navigate to:
- Local: `http://localhost:10000`
- Production: Your deployed URL

## Deployment Options

### Render (Recommended)

1. **Connect GitHub Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT src.app:app`
   - **Environment**: Python 3

3. **Set Environment Variables**
   - Add `OPENAI_API_KEY` in the Render dashboard
   - Set `FLASK_ENV=production`

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy from your main branch

### Docker

```bash
cd deployment/docker
docker-compose up -d
```

### Heroku

```bash
# Install Heroku CLI first
heroku create your-app-name
heroku config:set OPENAI_API_KEY=your_key_here
git push heroku main
```

## Development Setup

### Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Development Dependencies
```bash
# Install additional development tools
pip install pytest black flake8 mypy
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/
```

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for transcription | - | ✅ |
| `FLASK_ENV` | Flask environment | `development` | ❌ |
| `FLASK_DEBUG` | Enable debug mode | `True` | ❌ |
| `PORT` | Application port | `10000` | ❌ |
| `SECRET_KEY` | Flask secret key | `dev-secret-key` | ❌ |
| `LOG_LEVEL` | Logging level | `INFO` | ❌ |

### Audio Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `MAX_AUDIO_SIZE` | Maximum audio file size | `50MB` |
| `SUPPORTED_FORMATS` | Supported audio formats | `wav,mp3,webm,m4a` |
| `DEFAULT_LANGUAGE` | Default transcription language | `nl` |

## Troubleshooting

### Common Issues

#### 1. OpenAI API Key Error
```
ValueError: OPENAI_API_KEY environment variable is required
```
**Solution**: Ensure your `.env` file contains a valid OpenAI API key.

#### 2. Module Import Error
```
ModuleNotFoundError: No module named 'core'
```
**Solution**: Make sure you're running the app from the repository root directory.

#### 3. Audio Upload Error
```
⚠️ Geen bestand geselecteerd
```
**Solution**: Ensure you're uploading a supported audio format (wav, mp3, webm, m4a).

#### 4. Render Deployment Issues
- **Build fails**: Check that `requirements.txt` is in the repository root
- **Start command fails**: Verify the start command is `gunicorn --bind 0.0.0.0:$PORT src.app:app`
- **Environment variables**: Ensure `OPENAI_API_KEY` is set in Render dashboard

### Getting Help

1. **Check the logs**: Look at application logs for detailed error messages
2. **Verify environment**: Ensure all required environment variables are set
3. **Test locally**: Try running the application locally first
4. **Check dependencies**: Ensure all Python packages are installed correctly

## Performance Optimization

### Production Settings
```bash
# .env for production
FLASK_ENV=production
FLASK_DEBUG=false
LOG_LEVEL=WARNING
```

### Gunicorn Configuration
```bash
# For better performance
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.app:app
```

### Audio Processing
- Use compressed audio formats (mp3, m4a) for faster uploads
- Keep audio files under 25MB for optimal processing speed
- Consider preprocessing audio to remove silence

## Security Considerations

### Production Deployment
- Set a strong `SECRET_KEY`
- Use HTTPS in production
- Implement rate limiting for API endpoints
- Regularly update dependencies
- Monitor API usage and costs

### Data Privacy
- Audio files are processed by OpenAI's API
- Ensure compliance with medical data regulations
- Consider data retention policies
- Implement proper access controls

---

**Need help?** Check the [User Guide](USER_GUIDE.md) or open an issue on GitHub.

