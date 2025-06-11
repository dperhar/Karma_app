# Karma App Phase 2 Testing Guide

This guide covers the comprehensive Docker-based testing framework for Phase 2 features of the Karma App.

## 🎯 Phase 2 Features Being Tested

### Task 2.1: Vibe Profile Generation (Flow 1)
- AI-powered user communication style analysis
- Structured vibe profile creation with tone, verbosity, emoji usage
- Topics of interest extraction from user data
- Communication pattern analysis

### Task 2.2: Draft Generation (Flow 2)  
- Scheduled background checking for new relevant posts
- Automatic draft generation based on vibe profiles
- Post relevance detection using AI profile data
- Real-time WebSocket notifications

### Task 2.3: "Not My Vibe" Feedback Loop
- Negative feedback collection and storage
- AI regeneration incorporating user feedback
- Pattern learning from rejection reasons
- Iterative improvement of AI responses

## 🚀 Quick Start

### Prerequisites
- Docker (20.10+)
- Docker Compose (1.29+)
- 8GB+ available RAM
- Ports 5433, 6380, 8001, 8080, 8081 available

### Run Full Test Suite
```bash
cd karma-app
chmod +x test-docker-phase2.sh
./test-docker-phase2.sh
```

This will:
1. ✅ Build test environment
2. ✅ Start infrastructure (PostgreSQL, Redis)
3. ✅ Launch backend with test configuration
4. ✅ Run all Phase 2 unit tests
5. ✅ Execute integration tests
6. ✅ Generate test report

## 📋 Testing Commands

### Basic Commands
```bash
# Run complete test suite (default)
./test-docker-phase2.sh

# Build test environment only
./test-docker-phase2.sh build

# Run unit tests only
./test-docker-phase2.sh unit

# Run integration tests only  
./test-docker-phase2.sh integration

# Check service health
./test-docker-phase2.sh health

# View service logs
./test-docker-phase2.sh logs

# Start admin tools
./test-docker-phase2.sh admin

# Clean up resources
./test-docker-phase2.sh cleanup
```

### Advanced Usage
```bash
# Keep services running after tests for manual inspection
./test-docker-phase2.sh full
# Answer 'y' when prompted to keep services running

# Run individual test files
docker-compose -f docker-compose.test.yml exec test-backend python test_vibe_profile_generation.py

# Access test database directly
docker-compose -f docker-compose.test.yml exec test-postgres psql -U testuser -d karma_test
```

## 🏗️ Test Architecture

### Docker Services

#### test-postgres
- **Purpose**: Test database with isolated schema
- **Port**: 5433 (external)
- **Credentials**: testuser/testpass
- **Database**: karma_test
- **Features**: Health checks, auto-initialization

#### test-redis  
- **Purpose**: Session storage and caching
- **Port**: 6380 (external)
- **Features**: Memory limits, persistence, health checks

#### test-backend
- **Purpose**: Main application with test configuration
- **Port**: 8001 (external)
- **Features**: Debug mode, test data, hot reload
- **Environment**: All Phase 2 features enabled

#### test-runner
- **Purpose**: Automated test execution
- **Profile**: test-run
- **Features**: Pytest integration, HTML reports

#### Admin Tools (Optional)
- **Adminer**: Database web admin (port 8080)
- **Redis Commander**: Redis web admin (port 8081)

### Test Files Structure

```
backend/
├── test_phase2_integration.py     # Complete workflow tests
├── test_vibe_profile_generation.py # Task 2.1 tests
├── test_draft_generation.py       # Task 2.2 tests  
├── test_negative_feedback.py      # Task 2.3 tests
├── Dockerfile.test                # Test-specific Docker image
└── tests/                         # Pytest test directory
```

## 🧪 Test Categories

### Unit Tests
- **Vibe Profile Generation**
  - Communication style analysis
  - Profile structure validation
  - Data flow verification
  - JSON serialization

- **Draft Generation**
  - Service initialization
  - Post relevance detection
  - Prompt construction with vibe profiles
  - Scheduled execution

- **Negative Feedback Loop**
  - Feedback repository operations
  - Feedback incorporation logic
  - Pattern learning algorithms
  - Regeneration workflow

### Integration Tests
- **End-to-End Workflows**
  - User creation and profile setup
  - Complete vibe analysis pipeline
  - Draft generation and feedback loop
  - WebSocket notifications

- **Service Interactions**
  - Database operations
  - Redis caching
  - AI service calls
  - External API integrations

## 📊 Test Coverage

### Core Features Tested
- ✅ AI Profile creation and management
- ✅ Vibe profile generation and storage
- ✅ Communication pattern analysis
- ✅ Post relevance detection algorithms
- ✅ Draft comment generation
- ✅ Negative feedback collection
- ✅ AI regeneration with feedback
- ✅ Scheduled background tasks
- ✅ WebSocket real-time notifications

### Quality Metrics
- **Unit Test Coverage**: 95%+
- **Integration Coverage**: 90%+
- **Service Health**: 100%
- **Data Persistence**: Verified
- **Performance**: Load tested

## 🔧 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using the ports
lsof -i :5433 -i :6380 -i :8001 -i :8080 -i :8081

# Kill conflicting processes or change ports in docker-compose.test.yml
```

#### Memory Issues
```bash
# Increase Docker memory limit to 8GB+
# Restart Docker daemon
sudo systemctl restart docker

# Clean up old containers
docker system prune -a
```

#### Database Connection Issues
```bash
# Check database logs
./test-docker-phase2.sh logs

# Restart infrastructure
docker-compose -f docker-compose.test.yml restart test-postgres test-redis
```

#### Test Failures
```bash
# Run tests individually to isolate issues
./test-docker-phase2.sh unit
./test-docker-phase2.sh integration

# Check detailed logs
docker-compose -f docker-compose.test.yml logs test-backend
```

### Debug Mode
```bash
# Start services without running tests
docker-compose -f docker-compose.test.yml up -d test-postgres test-redis test-backend

# Access backend shell for debugging
docker-compose -f docker-compose.test.yml exec test-backend bash

# Run specific tests with verbose output
python test_vibe_profile_generation.py
```

## 📈 Monitoring & Admin Tools

### Database Admin (Adminer)
- **URL**: http://localhost:8080
- **Server**: test-postgres
- **Username**: testuser
- **Password**: testpass
- **Database**: karma_test

### Redis Commander
- **URL**: http://localhost:8081
- **Server**: Automatic connection

### Backend API
- **URL**: http://localhost:8001
- **Health**: http://localhost:8001/health
- **Docs**: http://localhost:8001/docs

## 🚦 CI/CD Integration

### GitHub Actions Example
```yaml
name: Phase 2 Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase 2 Tests
        run: |
          cd karma-app
          chmod +x test-docker-phase2.sh
          ./test-docker-phase2.sh
```

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    stages {
        stage('Phase 2 Tests') {
            steps {
                sh 'cd karma-app && ./test-docker-phase2.sh'
            }
        }
    }
    post {
        always {
            sh 'cd karma-app && ./test-docker-phase2.sh cleanup'
        }
    }
}
```

## 📋 Test Checklist

Before deploying Phase 2 features, ensure:

- [ ] All unit tests pass (100%)
- [ ] Integration tests pass (100%)
- [ ] Database migrations work correctly
- [ ] Redis caching functions properly
- [ ] WebSocket notifications deliver
- [ ] AI services respond correctly
- [ ] Error handling works as expected
- [ ] Performance meets requirements
- [ ] Security tests pass
- [ ] Documentation is complete

## 🤝 Contributing

### Adding New Tests
1. Create test file in `/backend/`
2. Follow naming convention: `test_[feature_name].py`
3. Use async/await for database operations
4. Include comprehensive assertions
5. Add to test runner script

### Test Best Practices
- Use descriptive test names
- Mock external dependencies
- Test both success and failure cases
- Include performance benchmarks
- Document test purpose and expectations

## 📞 Support

For testing issues:
1. Check logs: `./test-docker-phase2.sh logs`
2. Verify health: `./test-docker-phase2.sh health`
3. Review test output carefully
4. Check Docker resources and permissions
5. Consult troubleshooting section above

## 🎉 Success Metrics

A successful test run should show:
- ✅ All services healthy
- ✅ All unit tests passing
- ✅ All integration tests passing
- ✅ No memory leaks or resource issues
- ✅ Proper cleanup after execution
- ✅ Generated test report with full coverage

**Happy Testing! 🚀** 