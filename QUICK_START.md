# 🚀 Quick Start Guide

## ChatGPT Web App - Local Testing

### ✅ Your App is Running!

**Access Points:**
- 🌐 API Docs: http://localhost:8001/docs
- 🏥 Health Check: http://localhost:8001/health
- 📡 API Base: http://localhost:8001/api/v1/

### 📤 How to Upload & Search Your Files

#### Step 1: Get Your Export Files

**For ChatGPT:**
1. Go to https://chatgpt.com/
2. Click your profile → Settings → Data controls
3. Click "Export data"
4. Wait for the email with your `conversations.json`

**For Claude:**
1. Go to https://claude.ai/
2. Click your profile → Settings
3. Export your conversation history
4. Download the `conversations.json`

#### Step 2: Upload Files via API

**Upload ChatGPT Export:**
```bash
curl -X POST "http://localhost:8001/api/v1/uploads/chatgpt" \
  -F "file=@/path/to/conversations.json"
```

**Upload Claude Export:**
```bash
curl -X POST "http://localhost:8001/api/v1/uploads/claude" \
  -F "file=@/path/to/conversations.json"
```

**Or use the Swagger UI:**
1. Go to http://localhost:8001/docs
2. Find `/api/v1/uploads/chatgpt` or `/api/v1/uploads/claude`
3. Click "Try it out"
4. Choose your file and click "Execute"

#### Step 3: Search Your Conversations

**Search via API:**
```bash
# Full-text search
curl "http://localhost:8001/api/v1/search/?query=machine%20learning&mode=fts"

# With filters
curl "http://localhost:8001/api/v1/search/?query=python&mode=fts&provider=chatgpt&limit=10"
```

**Or use Swagger UI:**
1. Go to http://localhost:8001/docs
2. Find `/api/v1/search/`
3. Click "Try it out"
4. Enter your search query and parameters
5. Click "Execute"

### 🔍 Available Endpoints

**Uploads:**
- `POST /api/v1/uploads/chatgpt` - Upload ChatGPT exports
- `POST /api/v1/uploads/claude` - Upload Claude exports
- `GET /api/v1/uploads/history` - View upload history
- `GET /api/v1/uploads/status/{id}` - Check upload status

**Search:**
- `GET /api/v1/search/` - Main search endpoint
- `GET /api/v1/search/conversations` - Search conversation titles
- `GET /api/v1/search/stats` - Get search statistics

### 🎯 Search Modes

- **fts** (Full-Text Search): Fast keyword matching
- **vector** (Semantic): AI-powered similarity (not yet implemented)
- **hybrid**: Combines both approaches (not yet fully functional)

### 🗂️ Search Filters

- `provider`: Filter by 'chatgpt' or 'claude'
- `role`: Filter by 'user', 'assistant', or 'system'
- `date_from`: Filter from date (YYYY-MM-DD)
- `date_to`: Filter to date (YYYY-MM-DD)
- `limit`: Number of results (1-100)

### 🐳 Docker Commands

```bash
# Stop the app
docker-compose down

# Start the app
docker-compose up -d

# View logs
docker-compose logs -f app

# Restart just the app
docker-compose restart app

# Full reset (deletes all data)
docker-compose down -v && docker-compose up -d
```

### 📊 Database Access

```bash
# Connect to PostgreSQL
docker exec -it chatgpt_postgres psql -U chatgpt_user -d chatgpt_webapp

# List all conversations
SELECT id, title, provider, message_count FROM conversations;

# Search messages
SELECT content FROM messages WHERE content LIKE '%search term%' LIMIT 10;
```

### ⚠️ Current Limitations

1. **No Real Auth**: Using a default test user (will add auth later)
2. **File Processing Incomplete**: Upload endpoints exist but database insertion needs work
3. **Vector Search**: Not yet implemented
4. **Frontend**: Basic React app not yet connected to backend

### 🔨 Next Steps

To make this production-ready:
1. Implement file processor database integration
2. Add real authentication
3. Connect frontend to backend
4. Implement vector search
5. Add user management

### 💡 Tips

- Use the **Swagger UI** at http://localhost:8001/docs for easy testing
- Check logs with `docker-compose logs -f app` if something fails
- The database persists between restarts (unless you use `-v` flag)
- All data is local and private on your machine

### 🐛 Troubleshooting

**App won't start:**
```bash
docker-compose down -v
docker-compose up -d --build
```

**Can't connect to database:**
```bash
docker-compose restart postgres
docker-compose restart app
```

**Port already in use:**
Edit `docker-compose.yml` and change `8001:8000` to another port like `8002:8000`

---

**Ready to search!** 🎉

