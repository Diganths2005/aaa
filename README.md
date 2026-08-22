# TaxWise - AI-Powered Tax Filing Application

A modern web application for tax filing with an AI copilot to guide users through the entire ITR process.

## Project Structure

```
taxwise/
├── frontend/          # Next.js + TypeScript
├── backend/           # FastAPI + Python
└── docs/              # Documentation
```

## Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI, Python 3.10+, SQLalchemy, PostgreSQL
- **Database**: PostgreSQL
- **Cloud AI**: Google Gemini/Vertex AI (for future copilot integration)

## Features

### Phase 1: Foundation (Current)
- ✅ User Authentication (Login/Signup)
- ✅ Dashboard
- ✅ Tax Profile Creation
- ✅ Multi-step form for tax data collection
- ⏳ Data persistence

### Phase 2: Tax Engine
- Tax calculation engine
- ITR preview generation
- Form auto-filling

### Phase 3: ITR Filing
- ITR form generation
- E-filing integration
- Document management

### Phase 4: AI Copilot
- RAG-based support
- Real-time guidance
- Document processing

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL 14+
- Git

### Quick Start

#### 1. Setup Database
```bash
# Install PostgreSQL or use Docker
docker run -d \
  --name postgres \
  -e POSTGRES_USER=taxwise_user \
  -e POSTGRES_PASSWORD=taxwise_password \
  -e POSTGRES_DB=taxwise_db \
  -p 5432:5432 \
  postgres:15
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

#### 3. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Backend runs on http://localhost:8000
```

## API Documentation

Once backend is running, visit `http://localhost:8000/docs` for Swagger UI.

### Auth Endpoints
- `POST /api/v1/auth/signup` - Create new account
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - Logout

### Tax Profile Endpoints
- `POST /api/v1/tax-profiles` - Create tax profile
- `GET /api/v1/tax-profiles/current` - Get current user's profile
- `GET /api/v1/tax-profiles/{id}` - Get specific profile
- `PUT /api/v1/tax-profiles/{id}` - Update profile
- `DELETE /api/v1/tax-profiles/{id}` - Delete profile
- `POST /api/v1/tax-profiles/{id}/documents` - Upload documents

## User Flow

1. **Login/Signup** → Authenticate user
2. **Dashboard** → View overview and available actions
3. **Tax Profile** → Fill 6-step form:
   - Personal Information
   - Residential Status & Employment
   - Income Details
   - Investments & Deductions
   - Tax & Bank Details
   - Document Upload
4. **Dashboard** → Profile saved, ready for next steps

## Development

### Frontend Development
- Update components in `frontend/src/components/`
- Add pages in `frontend/src/pages/`
- Modify types in `frontend/src/types/`
- API calls via `frontend/src/lib/api.ts`

### Backend Development
- Database models in `backend/models/`
- Request schemas in `backend/schemas/`
- Routes in `backend/routes/`
- Business logic in utilities

### Database Migrations
Current setup uses SQLAlchemy with automatic table creation.

For production:
```bash
# Install alembic
pip install alembic

# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Testing

### Frontend Tests (TODO)
```bash
cd frontend
npm run test
```

### Backend Tests (TODO)
```bash
cd backend
pytest
```

## Deployment

### Frontend
```bash
cd frontend
npm run build
npm start
# Or deploy to Vercel, Netlify
```

### Backend
```bash
# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/taxwise_db
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:3000
```

## Contributing

1. Create a feature branch
2. Make changes
3. Submit a pull request

## License

MIT

## Support

For issues and questions, please open a GitHub issue.

---

**Built with ❤️ for simplifying tax filing**
