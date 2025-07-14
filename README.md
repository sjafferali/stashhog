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

### Docker Setup (Development)

```bash
docker-compose up
```

This will start both frontend and backend services with hot reload enabled.

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