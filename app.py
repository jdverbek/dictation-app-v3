"""
Top-level app.py for Render deployment compatibility
Imports and runs the enhanced medical dictation app from src/
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the enhanced app
from src.app import app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

