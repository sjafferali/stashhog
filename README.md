# StashHog

AI-powered content tagging and organization for Stash - automatically analyze and tag your media library using advanced AI models.

## Overview

StashHog enhances your Stash experience by providing intelligent content analysis and automated tagging. It uses OpenAI's vision models to analyze scenes and generate relevant tags, making your library more searchable and organized.

### Key Features

- **AI-Powered Scene Analysis**: Automatically analyze video scenes using OpenAI's GPT-4 Vision
- **Smart Tag Generation**: Generate contextual tags based on visual content
- **Batch Processing**: Process multiple scenes efficiently with queue management
- **Real-time Updates**: WebSocket support for live progress updates
- **Modern UI**: Clean, responsive interface built with React and Ant Design
- **Extensible Architecture**: Modular design for easy feature additions

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A running Stash instance
- OpenAI API key

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/stashhog.git
   cd stashhog
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   uvicorn app.main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   cp .env.example .env.local
   # Edit .env.local if needed
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Setup

StashHog can be run using Docker Compose with either SQLite (default) or PostgreSQL as the database.

#### Using SQLite (Default)

```bash
# Create a docker-compose.yml file with the following content:
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  stashhog:
    image: docker.io/sjafferali/stashhog:latest
    container_name: stashhog
    ports:
      - "8000:8000"
    environment:
      - APP_NAME=StashHog
      - DATABASE_URL=sqlite:///app/data/stashhog.db
      - STASH_URL=http://your-stash-instance:9999
      - STASH_API_KEY=your-stash-api-key
      - OPENAI_API_KEY=your-openai-api-key
      - OPENAI_MODEL=gpt-4-vision-preview
      - SECRET_KEY=change-this-to-a-random-secret-key
      - APP_ENVIRONMENT=production
    volumes:
      - ./stashhog-data:/app/data
    restart: unless-stopped

volumes:
  stashhog-data:
EOF

# Start the application
docker-compose up -d
```

#### Using PostgreSQL

```bash
# Create a docker-compose.postgres.yml file with the following content:
cat > docker-compose.postgres.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: stashhog-postgres
    environment:
      - POSTGRES_USER=stashhog
      - POSTGRES_PASSWORD=stashhog-password
      - POSTGRES_DB=stashhog
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stashhog"]
      interval: 10s
      timeout: 5s
      retries: 5

  stashhog:
    image: docker.io/sjafferali/stashhog:latest
    container_name: stashhog
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      - APP_NAME=StashHog
      - DATABASE_URL=postgresql://stashhog:stashhog-password@postgres:5432/stashhog
      - STASH_URL=http://your-stash-instance:9999
      - STASH_API_KEY=your-stash-api-key
      - OPENAI_API_KEY=your-openai-api-key
      - OPENAI_MODEL=gpt-4-vision-preview
      - SECRET_KEY=change-this-to-a-random-secret-key
      - APP_ENVIRONMENT=production
    restart: unless-stopped

volumes:
  postgres-data:
EOF

# Start the application with PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d
```

#### Docker Compose Commands

```bash
# Start services
docker-compose up -d                    # SQLite version
docker-compose -f docker-compose.postgres.yml up -d  # PostgreSQL version

# View logs
docker-compose logs -f stashhog

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: This will delete your data!)
docker-compose down -v
```

#### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | Database connection string | Yes | `sqlite:///app/data/stashhog.db` |
| `STASH_URL` | URL of your Stash instance | Yes | - |
| `STASH_API_KEY` | API key for Stash | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `OPENAI_MODEL` | OpenAI model to use | No | `gpt-4-vision-preview` |
| `SECRET_KEY` | Secret key for sessions | Yes | - |
| `APP_ENVIRONMENT` | Environment (development/production) | No | `production` |

#### Notes

- For SQLite, data is persisted in the `./stashhog-data` directory
- For PostgreSQL, data is persisted in a named Docker volume
- The application will automatically run database migrations on startup
- Make sure to change the `SECRET_KEY` to a random value for security
- Ensure your Stash instance is accessible from the Docker container

## Architecture

### Backend (FastAPI)

```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Core configuration
│   ├── models/       # Database models
│   └── services/     # Business logic
└── tests/            # Test suite
```

- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation
- **WebSockets**: Real-time communication

### Frontend (React + TypeScript)

```
frontend/
└── src/
    ├── components/   # Reusable UI components
    ├── pages/        # Route pages
    ├── services/     # API integration
    ├── store/        # State management (Zustand)
    ├── types/        # TypeScript types
    └── utils/        # Utility functions
```

- **React 18**: UI library
- **TypeScript**: Type safety
- **Ant Design**: Component library
- **Zustand**: State management
- **Vite**: Build tool

## Configuration

### Environment Variables

**Backend (.env)**
```env
APP_NAME=StashHog
DATABASE_URL=sqlite:///./stashhog.db
STASH_URL=http://localhost:9999
STASH_API_KEY=your-stash-api-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-vision-preview
SECRET_KEY=your-secret-key
```

**Frontend (.env.local)**
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=StashHog
```

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint and Prettier for TypeScript/React
- Write tests for new features
- Update documentation as needed

## Roadmap

- [ ] Multi-model support (Claude, Gemini, etc.)
- [ ] Custom tagging rules and templates
- [ ] Performer recognition
- [ ] Scene similarity detection
- [ ] Bulk operations UI
- [ ] Plugin system for extensions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Stash](https://github.com/stashapp/stash) - The amazing media organizer this project extends
- [OpenAI](https://openai.com) - For providing powerful vision models
- All contributors and users of this project