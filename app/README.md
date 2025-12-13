# 🎯 Billio Backend API

FastAPI ile geliştirilmiş abonelik takip platformu backend'i.

## 🚀 Özellikler

- Firebase Authentication
- Supabase PostgreSQL
- 44 REST API endpoint
- Premium subscription management
- AI-powered analysis (mock)
- Rate limiting & security

## 📦 Kurulum
```bash
# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# .env dosyasını doldur

# Çalıştır
uvicorn app.main:app --reload --port 8001
```

## 🔑 Environment Variables
```env
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
SUPABASE_URL=https://your_project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
DEBUG=False
ALLOWED_ORIGINS=https://yourdomain.com
```

## 📖 API Documentation

Swagger: `http://localhost:8001/docs`

## 🛠️ Tech Stack

- FastAPI
- Firebase Admin SDK
- Supabase
- Pydantic
- Python 3.12

## 📄 License

MIT