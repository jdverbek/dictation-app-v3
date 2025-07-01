# 🩺 Medical Dictation App

An intelligent medical dictation application that transforms audio recordings into structured medical reports with advanced AI analysis.

## 🚀 Quick Start

### Enhanced Version (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd jdverbek-dictation-app

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Install dependencies
pip install -r requirements.txt

# Run the enhanced application
python src/app.py
```

### Legacy Version
For the original version, see [legacy/README_LEGACY.md](legacy/README_LEGACY.md)

## 🆕 Enhanced Features

### Two-Part Raadpleging Flow
1. **🧠 Smart History Collection (Anamnese)**
   - Intelligent conversation analysis
   - Automatic symptom detection and correlation
   - Smarter than average physician in identifying relevant details
   - Extracts reason for encounter in concise format

2. **🔬 Structured Clinical Examination (Onderzoek)**
   - Intuitive dictation for technical investigations
   - Structured templates for ECG, TTE, exercise tests, etc.
   - Smart template filling with fixed order maintenance
   - Removes incomplete sentences when measurements not provided

### 🛡️ Safety Features
- **NEVER fabricates data** - Only extracts explicitly mentioned information
- Source validation for all extracted data
- Confidence scoring for reliability assessment
- Range validation for medical measurements

## 📋 Supported Investigation Types

- **ECG**: Rhythm, intervals, morphology analysis
- **Exercise Test**: Watts, heart rate, blood pressure, symptoms
- **TTE/TEE**: Complete echocardiographic assessment
- **Device Interrogation**: Pacemaker/ICD parameters
- **Holter**: 24-48 hour monitoring results
- **General Clinical**: Flexible templates for other investigations

## 📚 Documentation

- [📖 User Guide](docs/USER_GUIDE.md) - How to use the application
- [🔧 Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [📡 API Reference](docs/API_REFERENCE.md) - API endpoints documentation
- [👨‍💻 Development Guide](docs/DEVELOPMENT.md) - For developers and contributors
- [📝 Changelog](docs/CHANGELOG.md) - Version history and updates

## 🏗️ Architecture

```
src/
├── app.py                    # Main Flask application
├── core/                     # Core analysis modules
│   ├── history_analyzer.py   # Smart history collection
│   └── clinical_examiner.py  # Clinical examination system
├── api/                      # REST API endpoints
├── templates/                # UI templates
└── static/                   # Static assets
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m pytest tests/test_history_analyzer.py
python -m pytest tests/test_clinical_examiner.py
```

## 🚀 Deployment

### Local Development
```bash
python src/app.py
```

### Production (Render)
```bash
# Uses render.yaml configuration
git push origin main
```

### Docker
```bash
cd deployment/docker
docker-compose up
```

## 🔧 Configuration

Environment variables (see `.env.example`):
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `FLASK_ENV`: development/production
- `PORT`: Application port (default: 10000)

## 📊 Usage Examples

### History Analysis
```python
from src.core.history_analyzer import HistoryAnalyzer

analyzer = HistoryAnalyzer()
analysis = analyzer.analyze_conversation(transcript)
print(f"Reason for encounter: {analysis.reason_for_encounter}")
```

### Clinical Examination
```python
from src.core.clinical_examiner import ClinicalExaminer

examiner = ClinicalExaminer()
result = examiner.analyze_examination(transcript, "ECG")
print(result.formatted_report)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Important Notes

- **Medical Use**: This tool assists medical professionals but does not replace clinical judgment
- **Data Privacy**: Ensure compliance with medical data protection regulations (GDPR, HIPAA)
- **Validation**: Always review and validate generated reports before clinical use
- **API Key**: Requires OpenAI API access for transcription and analysis

## 📞 Support

- 📧 Email: [your-email@domain.com]
- 🐛 Issues: [GitHub Issues](../../issues)
- 📖 Documentation: [docs/](docs/)

---

**Version**: 2.0.0 (Enhanced)  
**Last Updated**: July 2025

