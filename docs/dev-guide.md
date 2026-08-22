# TaxWise - Project Overview

## What We've Built

A complete fullstack tax filing application foundation with:

### ✅ Frontend (Next.js + TypeScript)
- **Login/Signup Pages**: JWT authentication flow
- **Dashboard**: User welcome screen with quick actions
- **Tax Profile Wizard**: 6-step form for data collection
  - Personal Information
  - Residential Status & Employment  
  - Income Details
  - Investments & Deductions
  - Tax & Bank Details
  - Document Upload
- **State Management**: Zustand for auth state
- **API Integration**: Axios with interceptors for token handling
- **Styling**: Tailwind CSS for responsive design

### ✅ Backend (FastAPI + Python)
- **Authentication**: JWT-based auth with password hashing
- **Database Models**: User and TaxProfile with SQLAlchemy ORM
- **API Routes**: 
  - Auth: signup, login, logout, me
  - Tax Profiles: CRUD operations
  - Document Upload: Placeholder
- **Database**: PostgreSQL with SQLAlchemy
- **CORS**: Configured for frontend access
- **Swagger UI**: Auto-generated API documentation

### ✅ Infrastructure
- **Docker Support**: Dockerfiles for both frontend and backend
- **Docker Compose**: Full stack orchestration
- **Environment Configuration**: .env file support
- **Database**: PostgreSQL setup with Docker option

### ✅ Documentation
- **README.md**: Complete project overview
- **SETUP.md**: Step-by-step setup guide
- **ROADMAP.md**: 12-week development plan
- **API.md**: Full API documentation
- **dev-guide.md**: Developer reference

---

## Project Structure

```
taxwise/
├── frontend/
│   ├── src/
│   │   ├── pages/           # Next.js pages
│   │   │   ├── index.tsx
│   │   │   ├── login.tsx
│   │   │   ├── signup.tsx
│   │   │   ├── dashboard.tsx
│   │   │   ├── tax-profile.tsx
│   │   │   └── _app.tsx
│   │   ├── components/      # Reusable components
│   │   ├── lib/             # Utilities & API client
│   │   │   └── api.ts       # Axios instance & API calls
│   │   ├── store/           # Zustand store
│   │   │   └── auth.ts      # Auth state management
│   │   ├── types/           # TypeScript types
│   │   │   └── index.ts
│   │   └── styles/          # Global styles
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── backend/
│   ├── models/              # Database models
│   │   ├── user.py
│   │   └── tax_profile.py
│   ├── schemas/             # Request/response schemas
│   │   ├── user.py
│   │   └── tax_profile.py
│   ├── routes/              # API routes
│   │   ├── auth.py
│   │   └── tax_profile.py
│   ├── utils/               # Utilities
│   │   ├── auth.py          # JWT & password handling
│   │   └── common.py        # ID generation
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── docs/
│   ├── SETUP.md             # Setup instructions
│   ├── ROADMAP.md           # Development roadmap
│   ├── API.md               # API documentation
│   └── dev-guide.md         # Developer guide
│
├── README.md                # Project overview
├── docker-compose.yml       # Docker container orchestration
└── .gitignore
```

---

## Quick Start

### 1. Setup Database (Choose one)

**Using Docker:**
```bash
docker run -d --name taxwise_postgres \
  -e POSTGRES_USER=taxwise_user \
  -e POSTGRES_PASSWORD=taxwise_password \
  -e POSTGRES_DB=taxwise_db \
  -p 5432:5432 \
  postgres:15
```

**Using Docker Compose (all-in-one):**
```bash
docker-compose up -d
```

**Local PostgreSQL:**
- Install PostgreSQL
- Create user: `CREATE USER taxwise_user WITH PASSWORD 'taxwise_password';`
- Create database: `CREATE DATABASE taxwise_db OWNER taxwise_user;`

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# Backend: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Frontend: http://localhost:3000
```

### 4. Test the Flow

1. Go to `http://localhost:3000`
2. Click "Sign up"
3. Fill in details and create account
4. You'll be redirected to dashboard
5. Click "Create Profile"
6. Fill the 6-step form
7. Click "Complete & Save"
8. Data is saved to database!

---

## Key Features Implemented

### Authentication ✅
- User registration with validation
- Secure password hashing (bcrypt)
- JWT token generation
- Token-based API authorization
- Cookie-based token storage

### Tax Profile Management ✅
- Multi-step form wizard UI
- 6 comprehensive sections
- Form validation
- Progress tracking
- Data persistence to database

### API ✅
- RESTful endpoints
- Request/response validation
- Error handling
- Auto-generated Swagger docs
- CORS support

### Database ✅
- PostgreSQL integration
- SQLAlchemy ORM
- Automatic schema creation
- User-Profile relationships

### Frontend ✅
- Modern React with Next.js
- TypeScript for type safety
- Tailwind CSS styling
- State management with Zustand
- Axios API client
- Responsive design

---

## Next Steps

### Phase 2: Tax Engine (Recommended Next)
1. Build tax calculation logic
2. Add computation formulas for different income types
3. Create ITR preview generator
4. Implement refund/payable calculation

### Immediate Enhancements
1. Form validation improvements
2. Error handling & user feedback
3. Loading states & animations
4. Unit tests
5. API documentation improvements

---

## Technology Stack Summary

| Layer | Technologies |
|-------|--------------|
| Frontend | Next.js, TypeScript, Tailwind CSS, Zustand, Axios |
| Backend | FastAPI, Python 3.11, SQLAlchemy |
| Database | PostgreSQL 15 |
| Auth | JWT, bcrypt |
| Container | Docker, Docker Compose |
| Docs | Markdown |

---

## Development Workflow

### Making Changes to Frontend
1. Edit files in `frontend/src/`
2. Hot reload automatically refreshes `http://localhost:3000`
3. Check console for errors

### Making Changes to Backend
1. Edit files in `backend/`
2. Server auto-reloads with `--reload`
3. Check `http://localhost:8000/docs` for changes

### Database Changes
1. Modify models in `backend/models/`
2. Run server to auto-create tables
3. For migrations, use Alembic (future)

---

## Common Issues & Fixes

**Port already in use:**
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:3000 | xargs kill -9
```

**Database connection error:**
- Verify PostgreSQL is running
- Check credentials in `backend/.env`
- Ensure database exists

**Frontend can't reach backend:**
- Verify backend is running on port 8000
- Check `frontend/.env.local` configuration
- Clear browser cache

---

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)

---

## Git Workflow

```bash
# Initial setup
git init
git add .
git commit -m "Initial commit: TaxWise foundation"

# Feature branches
git checkout -b feature/tax-calculation
git commit -am "Add tax calculation engine"
git push origin feature/tax-calculation

# Merge back to main
git checkout main
git merge feature/tax-calculation
```

---

## Deployment

### Frontend (Vercel recommended)
```bash
npm run build
# Deploy to Vercel: vercel --prod
```

### Backend (AWS/GCP/Azure)
```bash
# Build image
docker build -t taxwise-backend .

# Push to registry and deploy
docker push <registry>/taxwise-backend
```

---

**Status**: Phase 1 Complete ✅
**Next Phase**: Tax Engine Implementation
**Timeline**: Ready for next sprint planning

For detailed setup instructions, see [SETUP.md](docs/SETUP.md)
For API documentation, see [API.md](docs/API.md)  
For roadmap, see [ROADMAP.md](docs/ROADMAP.md)
