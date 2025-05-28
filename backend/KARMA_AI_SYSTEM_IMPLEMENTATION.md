# Karma AI Comment Generation System

## 🎯 Overview

This document describes the implementation of the AI-powered comment generation system for Telegram integration. The system automatically generates draft comments from a defined persona (e.g., "Mark Zuckerberg") based on relevant posts from user's Telegram channels.

## 🏗️ Architecture Overview

### Core Components

1. **AI Comment Generation Engine** (`KarmaService`)
2. **Draft Comment Management** (`DraftCommentRepository`)
3. **Persona System** (User model extensions)
4. **Data Fetching Service** (Telegram integration)
5. **Background Scheduler** (Periodic tasks)
6. **WebSocket Notifications** (Real-time updates)

### Data Flow

```
Telegram Posts → Content Filter → AI Generation → Draft Storage → User Review → Posting
```

## 📋 Implemented Features

### ✅ Completed Components

#### 1. Database Models
- **DraftComment Model** (`models/ai/draft_comment.py`)
  - Stores AI-generated drafts with full lifecycle tracking
  - Status management: DRAFT → EDITED → APPROVED → POSTED
  - Links to original posts and users
  - Generation metadata storage

- **User Model Extensions** (`models/user/user.py`)
  - Persona configuration (name, style, interests)
  - AI model preferences
  - Telegram session management

#### 2. AI Generation Service (`services/domain/karma_service.py`)
- **Content Relevance Filtering**: Only generates comments for posts matching persona interests
- **Mock AI Integration**: Currently uses persona-based mock responses
- **Real AI Support**: Ready for Gemini/OpenAI integration
- **Context-Aware Prompts**: Constructs detailed prompts with persona information

#### 3. Draft Management
- **CRUD Operations**: Full lifecycle management of draft comments
- **Status Tracking**: DRAFT → EDITED → APPROVED → POSTED → FAILED_TO_POST
- **User Association**: All drafts linked to specific users
- **Editing Support**: Users can modify AI-generated text

#### 4. API Endpoints (`routes/api/draft_comments.py`)
- `GET /draft-comments` - List user's drafts
- `GET /draft-comments/{id}` - Get specific draft
- `PUT /draft-comments/{id}` - Update draft content
- `POST /draft-comments/{id}/approve` - Approve for posting
- `POST /draft-comments/{id}/post` - Post to Telegram (placeholder)

#### 5. Background Services
- **Scheduler Service** (`services/domain/scheduler_service.py`)
  - Random interval execution (30-240 minutes)
  - Graceful error handling and recovery
  - Async task management

- **Data Fetching Service** (`services/domain/data_fetching_service.py`)
  - Incremental Telegram data fetching
  - Integration with AI comment generation
  - WebSocket notifications for new content

#### 6. Testing Infrastructure
- **Setup Scripts**: Persona configuration automation
- **Full System Tests**: End-to-end functionality verification
- **Mock Mode**: Development without API keys

### 📊 Current System Status

```
✅ Backend server: Running
✅ Database: Connected and working  
✅ User persona: Configured (Mark Zuckerberg)
✅ AI generation: Working (mock mode)
✅ Content filtering: Working (interest-based)
✅ Draft management: Working
✅ WebSocket notifications: Configured
⚠️  API authentication: Not tested (requires auth)
⚠️  Real AI models: Not configured (using mock)
⚠️  Telegram integration: Not tested (requires session)
```

## 🔧 Configuration

### Mark Zuckerberg Persona Configuration

The system is configured with a "Mark Zuckerberg" persona:

```json
{
  "persona_name": "Mark Zuckerberg",
  "persona_style_description": "Visionary tech leader who speaks with passion about connecting people and building the future. Uses accessible language to explain complex concepts. Optimistic about technology's potential while acknowledging challenges. Focuses on long-term thinking and metaverse/VR innovations.",
  "persona_interests_json": [
    "Metaverse", "Virtual Reality", "VR", "AR", "Augmented Reality",
    "AI", "Artificial Intelligence", "Machine Learning", "Web3",
    "Blockchain", "NFT", "Social Networks", "Facebook", "Meta",
    "Instagram", "WhatsApp", "Future of Work", "Remote Work",
    "Digital Transformation", "Privacy", "Technology", "Innovation",
    "Startup", "Entrepreneurship", "Social Impact", "Connecting People",
    "Community Building", "Open Source", "Developer Tools",
    "Platform Economy", "Digital Economy"
  ]
}
```

### Sample AI Generated Comments (Mock Mode)

For VR/AI posts:
- "This is exactly the kind of innovation that will shape the future of human connection. The convergence of AR/VR technologies is bringing us closer to the metaverse vision."
- "Spatial computing represents a fundamental shift in how we'll interact with digital experiences. This is the foundation for the next computing platform."
- "Really exciting to see this progress! These advances in immersive technology will unlock new ways for people to connect and collaborate."

## 🚀 Getting Started

### 1. Setup Persona
```bash
python setup_mark_zuckerberg_persona.py
```

### 2. Run System Tests
```bash
python test_full_system.py
```

### 3. Start Server
```bash
python main.py
```

### 4. Test API Endpoints
```bash
curl http://localhost:8000/health
curl http://localhost:8000/draft-comments
```

## 📈 Usage Examples

### Generate Draft Comment
```python
karma_service = container.resolve(KarmaService)

post_data = {
    'text': 'Apple released new Vision Pro updates with improved spatial computing capabilities.',
    'channel': {'title': 'Tech News Channel'},
    'date': '2024-01-15T10:00:00'
}

draft = await karma_service.generate_draft_comment(
    original_message_id="msg_123",
    user_id=user.id,
    post_data=post_data
)
```

### Manage Draft Lifecycle
```python
# Edit draft
updated = await karma_service.update_draft_comment(
    draft_id, 
    DraftCommentUpdate(edited_text="Edited comment text")
)

# Approve for posting
approved = await karma_service.approve_draft_comment(draft_id)

# Post to Telegram (requires client)
posted = await karma_service.post_draft_comment(draft_id, telegram_client)
```

## 🔄 System Workflow

1. **Background Scheduler** triggers data fetching every 30-240 minutes
2. **Data Fetching Service** gets new posts from user's Telegram channels
3. **Content Filter** checks if posts match persona interests
4. **AI Service** generates relevant comments using persona style
5. **Draft Storage** saves generated comments with metadata
6. **WebSocket Notifications** alert frontend of new drafts
7. **User Review** allows editing and approval of drafts
8. **Telegram Posting** publishes approved comments

## 🛠️ Next Implementation Steps

### Phase 1: Real AI Integration
- [ ] Configure Gemini API key
- [ ] Test real AI comment generation
- [ ] Fine-tune prompts for quality

### Phase 2: Telegram Integration  
- [ ] Implement user session management
- [ ] Test incremental data fetching
- [ ] Implement comment posting to Telegram

### Phase 3: Scheduler Activation
- [ ] Enable automatic background data fetching
- [ ] Monitor system performance
- [ ] Implement error handling and recovery

### Phase 4: Frontend Integration
- [ ] Build draft management UI
- [ ] Implement real-time updates
- [ ] Add user settings for persona customization

## ⚠️ Important Notes

### Content Filtering
The system includes interest-based filtering to ensure AI only generates comments for relevant posts. Posts about cooking, sports, or other non-tech topics are automatically skipped.

### Mock Mode
Currently using mock AI responses for development. Real AI integration requires:
- API keys configuration
- Prompt optimization
- Rate limiting implementation

### Authentication
API endpoints require proper authentication in production. Current implementation uses placeholder auth checking.

### Telegram Rate Limits
When implementing real Telegram integration, respect API rate limits:
- Random intervals between requests
- Proper error handling for flood waits
- Session management for user accounts

## 📝 Database Schema

### DraftComments Table
```sql
CREATE TABLE draft_comments (
    id TEXT PRIMARY KEY,
    original_message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    persona_name TEXT,
    ai_model_used TEXT,
    original_post_text_preview TEXT,
    draft_text TEXT NOT NULL,
    edited_text TEXT,
    final_text_to_post TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    posted_telegram_message_id BIGINT,
    generation_params JSON,
    failure_reason TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Users Table (Extended)
```sql
ALTER TABLE users ADD COLUMN persona_name TEXT DEFAULT 'Default User';
ALTER TABLE users ADD COLUMN persona_style_description TEXT;
ALTER TABLE users ADD COLUMN persona_interests_json JSON;
```

## 🎯 Success Metrics

- **Content Relevance**: 100% of irrelevant posts correctly filtered
- **AI Quality**: Generated comments match persona style and interests  
- **System Reliability**: Background scheduler operates without interruption
- **User Experience**: Draft management workflow is intuitive and responsive
- **Performance**: Comment generation completes within 5 seconds

## 🔧 Development Tools

### Available Scripts
- `setup_mark_zuckerberg_persona.py` - Configure persona
- `test_ai_comment_generation.py` - Test AI generation 
- `test_full_system.py` - Complete system verification

### Logging
All components include comprehensive logging for debugging and monitoring:
- KarmaService operations
- Draft lifecycle changes  
- AI generation attempts
- Error conditions and recovery

This implementation provides a solid foundation for AI-powered comment generation with room for expansion and real-world deployment. 