# 🩺 Medical Dictation App - Legacy Version

⚠️ **This is the legacy version of the medical dictation app. For the enhanced version with intelligent analysis, see the main [README.md](../README.md)**

## Overview

This is the original medical dictation application that processes audio recordings into structured medical reports using OpenAI's Whisper and GPT-4.

## Features

- Audio transcription using Whisper
- Medical report generation for:
  - TTE (Transthoracic Echocardiography)
  - TEE (Transesophageal Echocardiography)
  - General consultations
  - Emergency consultations
- Live audio recording
- Template-based report formatting

## Quick Start

```bash
cd legacy/
export OPENAI_API_KEY="your_openai_api_key"
python app.py
```

Access the application at `http://localhost:10000`

## Files

- `app.py` - Main Flask application
- `templates/index.html` - User interface
- `requirements.txt` - Python dependencies
- `render.yaml` - Deployment configuration

## Migration Notice

🔄 **Consider upgrading to the enhanced version** which includes:
- Two-part raadpleging flow
- Intelligent conversation analysis
- Better clinical examination templates
- No data fabrication guarantee
- Improved accuracy and clinical relevance

See the main [README.md](../README.md) for migration instructions.

## Support

This legacy version is maintained for backward compatibility but new features will only be added to the enhanced version.

---

**Legacy Version**: 1.0.0  
**Status**: Maintenance mode  
**Recommended**: Upgrade to enhanced version

