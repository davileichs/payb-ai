# Slack Bot AI Chat Webhook

A Python-based Slack bot webhook that integrates with AI chat services (OpenAI and Ollama) to provide intelligent responses to Slack messages.

## Features

- **Slack Webhook Integration**: `/slack` endpoint for receiving Slack events
- **AI Chat Processing**: Support for OpenAI and Ollama AI services with provider-specific tool handling
- **Tool Integration**: Extensible tool system for AI capabilities
- **Dynamic Tool Selection**: AI chooses appropriate tools based on context and user needs
- **JWT Authentication**: Secure authentication for both Slack bot and AI chat services
- **Modular Architecture**: Clean separation between Slack bot and AI processing
- **Docker Deployment**: Easy containerized deployment

## Project Structure

```
payb/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py      # JWT token management
│   │   └── middleware.py       # Authentication middleware
│   ├── slack/
│   │   ├── __init__.py
│   │   ├── bot.py              # Slack bot logic
│   │   ├── events.py           # Slack event handlers
│   │   └── webhook.py          # Webhook endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── chat_processor.py   # Main AI chat processing
│   │   ├── agents/             # AI agent configurations
│   │   │   ├── __init__.py
│   │   │   ├── agent_manager.py
│   │   │   └── agents.json
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── openai_provider.py
│   │   │   └── ollama_provider.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Base tool interface
│   │   │   ├── weather.py      # Weather information tool
│   │   │   ├── provider_handle.py  # AI provider management tool
│   │   │   └── conversation_manager.py  # Conversation management tool
│   │   └── storage/
│   │       ├── __init__.py
│   │       └── redis_storage.py
│   └── api/
│       ├── __init__.py
│       ├── slack_routes.py     # Slack webhook routes
│       └── ai_routes.py        # AI chat external API routes
├── tests/
│   ├── __init__.py
│   ├── test_slack_bot.py
│   └── test_ai_chat.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Slack App credentials
- OpenAI API key (optional)
- Ollama instance (optional)

### Environment Setup

1. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running with Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run individually
docker build -t slack-ai-bot .
docker run -p 8000:8000 --env-file .env slack-ai-bot
```

### Running Locally

```bash
# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `POST /slack` - Slack webhook endpoint
- `POST /api/ai/chat` - External AI chat API
- `GET /api/ai/tools` - Get available AI tools
- `GET /health` - Health check endpoint

## Configuration

The bot supports configuration through environment variables:

- `SLACK_BOT_TOKEN` - Slack bot user OAuth token
- `SLACK_SIGNING_SECRET` - Slack app signing secret
- `OPENAI_API_KEY` - OpenAI API key
- `OLLAMA_BASE_URL` - Ollama instance URL
- `JWT_SECRET_KEY` - JWT signing secret
- `AI_PROVIDER` - Default AI provider (openai/ollama)
- `AI_TEMPERATURE` - AI response creativity/temperature (default: 0.7)
- `MAX_MESSAGES_PER_CONVERSATION` - Maximum messages per conversation (default: 100)

## Development

### Adding New Tools

1. Create a new tool class in `app/ai/tools/`
2. Inherit from `BaseTool`
3. Implement the required methods
4. Register the tool in `ChatProcessor`

### Testing

#### Unit Tests

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

#### Integration Tests

Run comprehensive integration tests through Docker:

```bash
# Using Makefile (recommended)
make integration-test

# Using shell script
./tests/run_integration_test.sh

# Manual execution
make docker-run &
sleep 20
python3 tests/integration_test.py
make docker-stop
```

The integration tests verify:
- ✅ Application health and connectivity
- ✅ LLM response functionality
- ✅ Provider switching (OpenAI/Ollama)
- ✅ Weather tool integration
- ✅ Agent name recognition (payb.ai)
- ✅ Live configuration reload

See [tests/README.md](tests/README.md) for detailed integration test documentation.

## Deployment

The project includes Docker configuration for easy deployment:

- **Development**: `docker-compose.yml` with hot-reload
- **Production**: `Dockerfile` optimized for production use

## Security

- JWT-based authentication for external API access
- Slack signature verification for webhook security
- Environment variable configuration for sensitive data
- Input validation and sanitization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details
