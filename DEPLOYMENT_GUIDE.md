# 🚀 Deployment Guide - GitHub + Render

## Quick Deployment Steps

### 1. GitHub Setup
```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit - Enhanced Medical Dictation App v2.0.0"

# Add your GitHub repository as remote
git remote add origin https://github.com/yourusername/your-repo-name.git

# Push to GitHub
git push -u origin main
```

### 2. Render Deployment

#### Option A: Enhanced Version (Recommended)
1. **Go to [Render Dashboard](https://dashboard.render.com)**
2. **Click "New" → "Web Service"**
3. **Connect your GitHub repository**
4. **Configure the service:**
   - **Name**: `medical-dictation-enhanced`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT src.app:app`
   - **Environment**: `Python 3`

5. **Set Environment Variables:**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `FLASK_ENV`: `production`
   - `FLASK_DEBUG`: `false`

6. **Deploy**: Click "Create Web Service"

#### Option B: Legacy Version (Backward Compatibility)
1. **Create another web service** (optional)
2. **Configure:**
   - **Name**: `medical-dictation-legacy`
   - **Build Command**: `pip install -r legacy/requirements.txt`
   - **Start Command**: `cd legacy && gunicorn --bind 0.0.0.0:$PORT app:app`

## Repository Structure Overview

```
jdverbek-dictation-app/
├── 📄 README.md                    # Main project documentation
├── 📄 render.yaml                  # Render deployment config
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment template
├── 📄 .gitignore                   # Git ignore rules
│
├── 📁 legacy/                      # Original app (v1.0.0)
│   ├── app.py                     # Original Flask app
│   ├── templates/index.html       # Original UI
│   └── README_LEGACY.md           # Legacy documentation
│
├── 📁 src/                        # Enhanced app (v2.0.0)
│   ├── app.py                     # Main Flask application
│   ├── core/                      # Core analysis modules
│   │   ├── history_analyzer.py    # Smart history collection
│   │   └── clinical_examiner.py   # Clinical examination system
│   └── templates/index.html       # Enhanced UI
│
├── 📁 docs/                       # Documentation
│   ├── INSTALLATION.md           # Setup instructions
│   ├── USER_GUIDE.md             # User documentation
│   └── CHANGELOG.md              # Version history
│
├── 📁 tests/                      # Test suite
│   └── test_history_analyzer.py   # Example tests
│
├── 📁 scripts/                    # Utility scripts
│   └── setup.sh                  # Setup automation
│
└── 📁 deployment/                 # Deployment configs
    └── docker/                    # Docker configuration
        ├── Dockerfile
        └── docker-compose.yml
```

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key (get from [OpenAI Platform](https://platform.openai.com/api-keys))

### Optional
- `FLASK_ENV`: `development` or `production` (default: `development`)
- `FLASK_DEBUG`: `true` or `false` (default: `true`)
- `PORT`: Application port (default: `10000`)

## Testing Your Deployment

### 1. Health Check
Visit: `https://your-app-name.onrender.com/health`

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-07-01T..."
}
```

### 2. Main Application
Visit: `https://your-app-name.onrender.com/`

You should see the enhanced medical dictation interface.

### 3. Test Recording
1. Select "Raadpleging (Enhanced)"
2. Choose "Anamnese" or "Onderzoek"
3. Upload a test audio file or use live recording
4. Verify the output is properly formatted

## Monitoring and Maintenance

### Render Dashboard
- **Logs**: Monitor application logs for errors
- **Metrics**: Check CPU, memory, and response times
- **Deployments**: View deployment history and status

### GitHub Integration
- **Auto-deploy**: Render automatically deploys when you push to main branch
- **Rollback**: Use Render dashboard to rollback to previous deployments
- **Branches**: Create feature branches for development

## Troubleshooting

### Common Issues

#### 1. Build Fails
```
Error: Could not find a version that satisfies the requirement...
```
**Solution**: Check `requirements.txt` format and Python version compatibility

#### 2. Start Command Fails
```
Error: No module named 'src'
```
**Solution**: Verify start command is `gunicorn --bind 0.0.0.0:$PORT src.app:app`

#### 3. OpenAI API Error
```
ValueError: OPENAI_API_KEY environment variable is required
```
**Solution**: Set `OPENAI_API_KEY` in Render dashboard environment variables

#### 4. Template Not Found
```
TemplateNotFound: index.html
```
**Solution**: Ensure templates are in `src/templates/` directory

### Getting Help
1. **Check Render logs** for detailed error messages
2. **Review documentation** in `docs/` folder
3. **Test locally** before deploying
4. **Open GitHub issue** for persistent problems

## Security Best Practices

### Production Settings
- Set `FLASK_ENV=production`
- Set `FLASK_DEBUG=false`
- Use strong `SECRET_KEY`
- Enable HTTPS (automatic on Render)

### API Key Management
- Never commit API keys to Git
- Use Render environment variables
- Rotate keys regularly
- Monitor API usage

### Data Privacy
- Audio files processed by OpenAI API
- Ensure GDPR/HIPAA compliance
- Implement data retention policies
- Use secure connections only

## Scaling Considerations

### Performance Optimization
- Use multiple Gunicorn workers: `--workers 2`
- Increase timeout for long audio files: `--timeout 120`
- Monitor memory usage for large files
- Consider CDN for static assets

### Cost Management
- Monitor OpenAI API usage
- Use Render's starter plan for development
- Upgrade to professional plan for production
- Implement request rate limiting

---

## 🎉 You're Ready to Deploy!

Your enhanced medical dictation app is now ready for professional deployment with:
- ✅ Professional repository structure
- ✅ Enhanced two-part raadpleging flow
- ✅ Comprehensive documentation
- ✅ Automated deployment configuration
- ✅ Safety features (no data fabrication)
- ✅ Backward compatibility with legacy version

**Next Steps:**
1. Push to GitHub
2. Deploy on Render
3. Test with real medical recordings
4. Share with colleagues for feedback
5. Monitor and iterate based on usage

