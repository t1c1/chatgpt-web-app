# ChatGPT Web App

A modern web application for searching and managing ChatGPT and Claude conversation exports with advanced search capabilities including full-text search, semantic search, and hybrid search modes.

## ✨ Features

### 🔍 Advanced Search
- **Full-Text Search (FTS)**: Lightning-fast keyword search using PostgreSQL FTS5
- **Semantic Search**: AI-powered similarity search using embeddings
- **Hybrid Search**: Best of both worlds combining FTS and semantic search
- **Advanced Filtering**: By provider, role, date ranges, projects

### 🎨 Beautiful UI
- Modern, responsive design inspired by your existing `safe-historical-search`
- Interactive filtering with clickable pills
- Real-time search with conversation context
- Mobile-friendly interface

### 📁 Multi-Provider Support
- **ChatGPT**: Full support for ChatGPT conversation exports
- **Claude**: Complete Claude conversation export processing
- **Mixed Exports**: Handle multiple accounts from both providers

### 🔒 Privacy & Security
- **Local-First**: Data stays on your infrastructure
- **Multi-Tenant**: Secure user isolation
- **API Access**: RESTful API with authentication
- **File Upload**: Secure processing of export files

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd chatgpt-web-app
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start the application:**
   ```bash
   ./setup.sh
   ```

4. **Access the web app:**
   - Web interface: http://localhost:8000
   - API documentation: http://localhost:8000/docs

### Manual Installation

1. **Install dependencies:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Setup PostgreSQL:**
   ```bash
   # Install PostgreSQL with pgvector extension
   # Create database and run migrations
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database settings
   ```

4. **Run the application:**
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📊 Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with pgvector for vector search
- **Authentication**: JWT tokens with user sessions
- **Caching**: Redis for performance optimization
- **File Processing**: Async file upload and processing

### Database Schema
- **Users**: Multi-tenant user management
- **Projects**: Organize conversations into projects
- **Conversations**: Normalized conversation metadata
- **Messages**: Individual messages with FTS indexing
- **Embeddings**: Vector embeddings for semantic search
- **Search Logs**: Analytics and usage tracking

### Search Capabilities
- **FTS**: PostgreSQL full-text search with ranking
- **Vector**: Cosine similarity using pgvector
- **Hybrid**: Combined scoring with configurable weights
- **Context**: Conversation context and threading

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Application secret key | Required |
| `POSTGRES_*` | Database connection settings | Required |
| `REDIS_*` | Redis connection settings | Optional |
| `EMBEDDING_MODEL` | Embedding model for semantic search | Optional |

### Search Modes

1. **FTS Mode**: Traditional full-text search
   - Fast keyword matching
   - Highlighted snippets
   - Date and role filtering

2. **Vector Mode**: Semantic similarity search
   - AI-powered understanding
   - Concept-based matching
   - Configurable similarity thresholds

3. **Hybrid Mode**: Combined search
   - Best of both approaches
   - Configurable weighting (alpha parameter)
   - Optimal relevance scoring

## 📁 File Processing

### Supported Formats
- **ChatGPT**: `conversations.json`, `shared_conversations.json`, `message_feedback.json`
- **Claude**: `conversations.json`, `projects.json`, `users.json`
- **Archives**: ZIP files containing export data

### Processing Features
- **Robust Parsing**: Handles format variations
- **Metadata Extraction**: Preserves all conversation metadata
- **Incremental Updates**: Add new exports without duplication
- **Error Handling**: Graceful handling of malformed data

## 🔐 Security

### Authentication
- JWT-based authentication
- Secure password hashing
- Session management
- API key support for programmatic access

### Data Protection
- SQL injection prevention
- XSS protection
- File upload validation
- Rate limiting
- Input sanitization

## 📈 Monitoring & Analytics

### Built-in Analytics
- Search usage statistics
- Performance metrics
- User activity tracking
- Popular search terms

### External Monitoring
- Structured logging
- Health check endpoints
- Metrics endpoints
- Error tracking integration

## 🚀 Deployment

### Production Deployment
1. **Database**: Production PostgreSQL instance
2. **Caching**: Redis cluster for scalability
3. **Storage**: S3 or similar for file uploads
4. **CDN**: For static assets and performance
5. **Monitoring**: Prometheus, Grafana, Sentry

### Scaling Considerations
- **Horizontal Scaling**: Multiple app instances
- **Database**: Read replicas for search queries
- **Caching**: Redis clustering
- **File Storage**: Distributed file system

## 🔮 Roadmap

### Phase 1: Core Features ✅
- [x] Database migration to PostgreSQL
- [x] FastAPI backend with async support
- [x] Multi-provider export processing
- [x] Advanced search capabilities

### Phase 2: Enhanced Features
- [ ] User authentication and multi-tenancy
- [ ] Modern React frontend
- [ ] Real-time search with WebSockets
- [ ] Mobile PWA support

### Phase 3: Advanced Features
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard
- [ ] API marketplace
- [ ] Plugin system

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style
- **Backend**: Black, isort, flake8
- **Frontend**: ESLint, Prettier
- **Database**: Alembic migrations
- **Documentation**: Markdown with proper formatting

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built on the excellent work from:
- [safe-historical-search](https://github.com/t1c1/safe-historical-search)
- [chatgpt-export-search](https://github.com/t1c1/chatgpt-export-search)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://postgresql.org/)
- [pgvector](https://github.com/pgvector/pgvector)

---

**Made with ❤️ for AI conversation enthusiasts**




