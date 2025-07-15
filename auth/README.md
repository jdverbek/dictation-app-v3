# Medical Authentication Platform

A secure, GDPR/HIPAA compliant authentication system for medical applications.

## Features

- 🔐 Secure user registration and authentication
- 📋 GDPR compliance with consent management
- 🛡️ PBKDF2 password hashing with salt
- 📊 Comprehensive audit logging
- 🎨 Professional, responsive web interface
- 🔄 Session-based authentication
- 🌐 CORS enabled for API integration

## Quick Deploy

### Deploy to Render

1. Fork this repository to your GitHub account
2. Go to [Render](https://render.com) and create a new account
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
6. Add environment variable:
   - `SECRET_KEY`: Generate a random secret key
7. Deploy!

### Deploy to Railway

1. Fork this repository to your GitHub account
2. Go to [Railway](https://railway.app) and create an account
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your forked repository
5. Railway will automatically detect the configuration from `railway.json`
6. Add environment variable:
   - `SECRET_KEY`: Generate a random secret key
7. Deploy!

### Deploy to Heroku

1. Fork this repository to your GitHub account
2. Go to [Heroku](https://heroku.com) and create an account
3. Create a new app
4. Connect to your GitHub repository
5. Enable automatic deploys
6. Add environment variable in Settings → Config Vars:
   - `SECRET_KEY`: Generate a random secret key
7. Deploy!

### Deploy to Vercel

1. Fork this repository to your GitHub account
2. Go to [Vercel](https://vercel.com) and create an account
3. Import your GitHub repository
4. Vercel will automatically detect the configuration from `vercel.json`
5. Add environment variable:
   - `SECRET_KEY`: Generate a random secret key
6. Deploy!

## Local Development

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd medical-auth-render
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export DATABASE_URL="medical_auth.db"
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser to `http://localhost:5000`

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/profile` - Get user profile

### Health Check

- `GET /health` - Health check endpoint

## Environment Variables

- `SECRET_KEY` - Flask secret key for session management (required)
- `DATABASE_URL` - Database file path (default: medical_auth.db)
- `PORT` - Port to run the application (default: 5000)

## Security Features

- PBKDF2 password hashing with 100,000 iterations
- Secure session management
- GDPR consent tracking
- Comprehensive audit logging
- Input validation and sanitization
- CORS protection

## Database Schema

### Users Table
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email address
- `first_name` - User's first name
- `last_name` - User's last name
- `password_hash` - Hashed password
- `salt` - Password salt
- `created_at` - Account creation timestamp
- `last_login` - Last login timestamp
- `is_active` - Account status
- `consent_given` - GDPR consent flag
- `consent_date` - GDPR consent timestamp

### Audit Logs Table
- `id` - Primary key
- `user_id` - Foreign key to users table
- `action` - Action performed
- `details` - Action details
- `ip_address` - User's IP address
- `user_agent` - User's browser information
- `timestamp` - Action timestamp

## Integration with Your Medical App

To integrate this authentication system with your existing medical transcription app:

1. Deploy this authentication platform using one of the methods above
2. Update your medical app to use the authentication API endpoints
3. Store the authentication platform URL in your app's configuration
4. Use session-based authentication or implement JWT tokens for API calls

Example integration:

```javascript
// Register a new user
const response = await fetch('https://your-auth-platform.com/api/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'user123',
    email: 'user@example.com',
    first_name: 'John',
    last_name: 'Doe',
    password: 'securepassword',
    consent_given: true
  }),
  credentials: 'include'
});

// Login user
const loginResponse = await fetch('https://your-auth-platform.com/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'user123',
    password: 'securepassword'
  }),
  credentials: 'include'
});
```

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the GitHub repository.

