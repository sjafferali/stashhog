# Task 01: Project Setup and Initial Structure

## Current State
- Repository exists at `/stashhog` with only:
  - `oldscript/analyze_scenes.py` - Legacy Python script for scene analysis
  - `.git` directory
  - No project structure or configuration files

## Objective
Create the foundational project structure for StashHog, including directory layout, configuration files, and initial documentation.

## Requirements

### Directory Structure
Create the following directory structure:
```
stashhog/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       └── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   └── services/
│   │       └── __init__.py
│   ├── tests/
│   │   └── __init__.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml (for development only)
```

### Backend Configuration

1. **requirements.txt** should include:
   - fastapi==0.104.1
   - uvicorn[standard]==0.24.0
   - sqlalchemy==2.0.23
   - alembic==1.12.1
   - pydantic==2.5.0
   - pydantic-settings==2.1.0
   - python-multipart==0.0.6
   - python-jose[cryptography]==3.3.0
   - passlib[bcrypt]==1.7.4
   - stashapi==0.1.0
   - openai==1.3.7
   - httpx==0.25.2
   - websockets==12.0
   - apscheduler==3.10.4
   - python-dotenv==1.0.0

2. **app/main.py** - Basic FastAPI application with:
   - CORS middleware configuration
   - Health check endpoint
   - API router registration
   - Startup/shutdown events

3. **app/core/config.py** - Settings management using Pydantic:
   - Environment variable loading
   - Configuration validation
   - Default values

4. **.env.example** with:
   ```
   # Application
   APP_NAME=StashHog
   DEBUG=False
   
   # Database
   DATABASE_URL=sqlite:///./stashhog.db
   
   # Stash API
   STASH_URL=http://localhost:9999
   STASH_API_KEY=
   
   # OpenAI
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4
   
   # Security
   SECRET_KEY=your-secret-key-here
   ```

### Frontend Configuration

1. **package.json** with:
   - React 18.2.0
   - TypeScript 5.3.0
   - Vite 5.0.0
   - Ant Design 5.12.0
   - Zustand 4.4.7
   - Axios 1.6.2
   - React Router 6.20.0
   - Development tools (ESLint, Prettier)

2. **tsconfig.json** - TypeScript configuration:
   - Strict mode enabled
   - Path aliases configured
   - JSX support for React

3. **vite.config.ts** - Vite configuration:
   - React plugin
   - Path aliases
   - Proxy configuration for API

4. **App.tsx** - Root component with:
   - Router setup
   - Global error boundary
   - Theme provider
   - Basic layout structure

### Documentation

1. **README.md** - Project documentation including:
   - Project overview
   - Quick start guide
   - Development setup
   - Architecture overview
   - Contributing guidelines

2. **.gitignore** - Comprehensive ignore file for:
   - Python artifacts (__pycache__, *.pyc, .env)
   - Node modules and build outputs
   - IDE configurations
   - OS-specific files

### Development Tools

1. **docker-compose.yml** for development:
   - Backend service with hot reload
   - Frontend service with hot reload
   - Volume mounts for code
   - Environment variable configuration

## Expected Outcome

After completing this task:
- Complete project structure is in place
- All configuration files are created
- Basic FastAPI app runs on http://localhost:8000
- Basic React app runs on http://localhost:5173
- Docker Compose can start both services
- README provides clear setup instructions

## Integration Points
- Backend and frontend can communicate via configured proxy
- Environment variables are properly loaded
- Database connection is configured (but not initialized)
- All dependencies are specified and installable

## Success Criteria
1. `cd backend && pip install -r requirements.txt` completes successfully
2. `cd frontend && npm install` completes successfully
3. `uvicorn app.main:app --reload` starts the backend
4. `npm run dev` starts the frontend
5. `docker-compose up` starts both services
6. Health check endpoint returns 200 OK
7. No linting errors in initial code