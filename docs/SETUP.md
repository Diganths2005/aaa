## Tax Profile data upgrade

The AY 2026-27 profile stores repeatable, typed sections for salary, pension, house property, other income, capital gains, business/professional income, foreign income/assets, investments, deductions, tax payments, bank accounts, and voluntary document references. It records the flags needed by a future ITR-1/2/3/4 eligibility step, but it does not select an ITR or calculate tax yet.

For an existing PostgreSQL database, apply `backend/migrations/001_itr_profile_upgrade.sql` before deploying the updated backend. The migration only adds columns and keeps existing rows. Local environment files, PAN values, and complete bank account numbers must not be committed or logged.
# TaxWise Setup Guide

## Prerequisites
Ensure you have the following installed:
- Node.js 18+ (https://nodejs.org/)
- Python 3.10+ (https://www.python.org/)
- PostgreSQL 14+ (https://www.postgresql.org/)
- Git (https://git-scm.com/)

## Database Setup

### Option 1: Local PostgreSQL
1. Install PostgreSQL from https://www.postgresql.org/download/
2. Create a database and user:
```sql
CREATE USER taxwise_user WITH PASSWORD 'taxwise_password';
CREATE DATABASE taxwise_db OWNER taxwise_user;
GRANT ALL PRIVILEGES ON DATABASE taxwise_db TO taxwise_user;
```

### Option 2: Docker
```bash
docker run -d \
  --name taxwise_postgres \
  -e POSTGRES_USER=taxwise_user \
  -e POSTGRES_PASSWORD=taxwise_password \
  -e POSTGRES_DB=taxwise_db \
  -p 5432:5432 \
  postgres:15
```

## Backend Setup

### 1. Navigate to backend directory
```bash
cd backend
```

### 2. Create virtual environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
Copy `.env.example` to `.env` and update values:
```bash
cp .env.example .env
```

### 5. Run the server
```bash
python main.py
```

The backend will start at `http://localhost:8000`

Test the API: `http://localhost:8000/docs`

## Frontend Setup

### 1. Navigate to frontend directory
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Configure environment (optional)
Create `.env.local` if needed:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Run development server
```bash
npm run dev
```

The frontend will start at `http://localhost:3000`

## Testing the Application

### 1. Open browser
Go to `http://localhost:3000`

### 2. Create an account
- Click "Sign up"
- Fill in your details
- Click "Sign up"

### 3. Access Dashboard
- You'll be automatically redirected to the dashboard
- Click "Create Profile" to start filling tax information

### 4. Fill Tax Profile
Follow the 6-step form:
1. Personal Information
2. Residential Status & Employment
3. Income Details
4. Investments & Deductions
5. Tax & Bank Details
6. Document Upload

### 5. Complete
Click "Complete & Save" to save your profile (data will be stored in database)

## Troubleshooting

### Frontend can't reach backend
- Ensure backend is running on `http://localhost:8000`
- Check `frontend/.env.local` has correct `NEXT_PUBLIC_API_URL`

### Database connection error
- Verify PostgreSQL is running
- Check credentials in `backend/.env`
- Ensure database exists: `CREATE DATABASE taxwise_db;`

### Port already in use
```bash
# Find and kill process using port
# On Windows (for port 3000):
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# On Mac/Linux:
lsof -ti:3000 | xargs kill -9
```

### Python package installation issues
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install packages individually
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib python-dotenv pydantic python-multipart
```

## Next Steps

1. **Review Code**: Explore the structure in both frontend and backend
2. **Modify Data Fields**: Add more fields to the tax profile if needed
3. **Database Queries**: Add custom queries for analytics
4. **API Enhancement**: Add more endpoints for ITR calculation
5. **Frontend Components**: Create reusable components
6. **Testing**: Write unit and integration tests

## Useful Commands

### Backend
```bash
# Run with hot reload (development)
python main.py

# Run with Uvicorn directly
uvicorn main:app --reload

# API docs
http://localhost:8000/docs
http://localhost:8000/redoc
```

### Frontend
```bash
# Development
npm run dev

# Build
npm run build

# Production
npm start

# Type checking
npm run type-check

# Lint
npm run lint
```

## Additional Resources

- Next.js Docs: https://nextjs.org/docs
- FastAPI Docs: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PostgreSQL: https://www.postgresql.org/docs/
- Tailwind CSS: https://tailwindcss.com/docs

## Support

For issues or questions, refer to the main README.md or create an issue on GitHub.
