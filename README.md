# 🤖 Karma App - Digital Twin System

AI-powered Telegram comment management system with digital twin personalities.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose

### 🏃‍♂️ Instant Launch

```bash
# Clone the repository
git clone <your-repo-url>
cd karma-app

# Quick start (one command setup)
make quickstart

# Or manually:
make dev
```

**That's it!** Your application will be running at:
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000  
- 📚 **API Docs**: http://localhost:8000/docs
- 🗄️ **Database**: localhost:5432

## 🐳 Docker Commands

### Development
```bash
make dev           # Start development environment
make dev-logs      # View development logs
make dev-down      # Stop development environment
```

### Production
```bash
make prod          # Start production environment
make prod-down     # Stop production environment
```

### Database
```bash
make db-init       # Initialize database
make db-shell      # Connect to PostgreSQL
make db-backup     # Create database backup
```

### Utilities
```bash
make status        # Show container status
make logs          # View all logs
make clean         # Clean up Docker resources
make help          # Show all available commands
```

## 🏗️ Architecture

```
🐳 Docker Container Architecture:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Frontend      │  │    Backend      │  │   PostgreSQL    │
│   (Next.js)     │  │   (FastAPI)     │  │    Database     │
│   Port: 3000    │  │   Port: 8000    │  │   Port: 5432    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │      Redis      │
                    │   (Optional)    │
                    │   Port: 6379    │
                    └─────────────────┘
```

## 🔧 Features

### Digital Twin Analysis
- **Communication Style Analysis**: Patterns, emoji usage, punctuation
- **Interest Extraction**: Topic categorization, keyword analysis
- **Personality Modeling**: AI-powered persona generation
- **Real-time Processing**: WebSocket notifications

### Technical Stack
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11, PostgreSQL
- **Containerization**: Docker, Docker Compose
- **AI Integration**: OpenAI GPT, Gemini API
- **Real-time**: WebSocket connections

## 📝 Environment Variables

### Backend (.env)
```bash
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/karma_app
IS_DEVELOP=true
FRONTEND_URL=http://localhost:3000
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

## 🧪 Testing

```bash
# Run backend tests
make shell-backend
python -m pytest

# Test API endpoints
curl http://localhost:8000/health
```

## 📊 Development Workflow

1. **Start Development Environment**:
   ```bash
   make dev
   ```

2. **View Logs** (in separate terminal):
   ```bash
   make dev-logs
   ```

3. **Make Changes**: Code changes are automatically reloaded in both frontend and backend

4. **Database Operations**:
   ```bash
   make db-shell    # Access database
   make db-init     # Initialize tables
   ```

5. **Stop Environment**:
   ```bash
   make dev-down
   ```

## 🔍 Troubleshooting

### Port Conflicts
```bash
# Check what's using ports
lsof -i :3000
lsof -i :8000

# Clean up Docker
make clean
```

### Container Issues
```bash
# Check container status
make status

# View logs
make logs

# Restart services
make restart
```

### Database Issues
```bash
# Reset database
make dev-down
docker volume rm karma-app_postgres_dev_data
make dev
```

## 📦 Production Deployment

```bash
# Build and start production environment
make prod

# Monitor production logs
docker-compose logs -f

# Scale services if needed
docker-compose up --scale backend=3 -d
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Start development environment: `make dev`
4. Make your changes
5. Run tests: `make test`
6. Commit your changes: `git commit -m 'Add some AmazingFeature'`
7. Push to the branch: `git push origin feature/AmazingFeature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

---

**🚀 Happy coding with Docker! No more manual setup headaches!** 🐳 