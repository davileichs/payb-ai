# Conversation History System

## Overview

The Slack Bot AI Chat application includes a comprehensive conversation history system that maintains chat context for AI models while keeping it private and inaccessible to external users. This system ensures that AI models have access to conversation context for better responses while maintaining user privacy.

## Architecture

### Core Components

1. **ConversationManager** (`app/ai/conversation_manager.py`)
   - Manages conversation lifecycle and storage
   - Handles conversation creation, updates, and cleanup
   - Provides context for AI processing

2. **Conversation** (`app/ai/conversation_manager.py`)
   - Represents a complete conversation session
   - Stores messages with metadata and timestamps
   - Manages conversation state and limits

3. **Message** (`app/ai/conversation_manager.py`)
   - Individual message representation
   - Includes role, content, timestamp, and metadata
   - Supports different message types (user, assistant, system, tool)

4. **Storage Layer** (`app/ai/storage/`)
   - Redis-based persistence for production
   - In-memory fallback for development
   - Automatic TTL and cleanup

## Features

### Privacy & Security
- **AI-Only Access**: Conversation history is only accessible to AI processing
- **No External Exposure**: External API users cannot access conversation history
- **Automatic Cleanup**: Conversations expire after 24 hours
- **Message Limits**: Maximum 100 messages per conversation to prevent memory issues

### Context Management
- **Smart Trimming**: Keeps recent messages while maintaining context
- **Role Filtering**: Provides clean context for LLM consumption
- **Metadata Tracking**: Stores provider, model, and execution information
- **Tool Integration**: Tracks tool execution results in conversation history

### Storage Options
- **Redis (Production)**: Persistent storage with automatic expiration
- **In-Memory (Development)**: Fast local storage for development
- **Automatic Fallback**: Gracefully falls back to in-memory if Redis unavailable

## How It Works

### 1. Message Processing Flow

```
User Message → ConversationManager → AI Processing → Response Storage
     ↓              ↓                    ↓              ↓
  Create/Get    Add to History    Generate AI      Store Response
  Conversation   (User Message)    Response        (AI Message)
```

### 2. Context Retrieval

When processing a message, the system:
1. Retrieves existing conversation or creates new one
2. Adds user message to conversation
3. Gets conversation context (last 20 messages)
4. Sends context to AI model for processing
5. Stores AI response in conversation
6. Returns response to user

### 3. Storage Management

- **Manual Cleanup**: Conversations are cleaned up via API endpoints
- **Memory Management**: Long conversations are trimmed to prevent memory issues
- **Message Limits**: Maximum messages per conversation is configurable

## API Endpoints

### Internal (AI Processing Only)
- Conversation history is automatically managed during AI processing
- No direct access to conversation data from external APIs
- Context is limited to last 20 messages for LLM processing

### Management (Admin Only)
- `DELETE /api/ai/conversations/{user_id}/{channel_id}` - Clear specific conversation
- `GET /api/ai/conversations/stats` - Get conversation statistics
- `GET /api/ai/conversations/config` - Get conversation configuration
- `POST /api/ai/conversations/cleanup` - Clean up conversations (keep N most recent)
- `POST /api/ai/conversations/cleanup/all` - Clean up all conversations

## Configuration

### Environment Variables
```bash
# Redis Configuration (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Conversation History Configuration
MAX_MESSAGES_PER_CONVERSATION=100
```

### Storage Selection
- **Redis Available**: Uses Redis for persistent storage
- **Redis Unavailable**: Falls back to in-memory storage
- **Automatic Detection**: System automatically detects and configures storage

## Data Structure

### Conversation Object
```python
@dataclass
class Conversation:
    id: str                    # Unique conversation identifier
    user_id: str              # Slack user ID
    channel_id: str           # Slack channel ID
    provider: str             # AI provider (openai/ollama)
    model: str                # AI model name
    messages: List[Message]   # List of messages
    created_at: datetime      # Creation timestamp
    updated_at: datetime      # Last update timestamp
    metadata: Dict            # Additional metadata
```

### Message Object
```python
@dataclass
class Message:
    role: str                 # Message role (user/assistant/system/tool)
    content: str              # Message content
    timestamp: datetime       # Message timestamp
    metadata: Dict            # Additional metadata
```

## Security Considerations

### Data Privacy
- **No External Access**: Conversation history is never exposed through external APIs
- **Internal Only**: Only AI processing components can access conversation data
- **Automatic Cleanup**: Sensitive data is automatically removed after expiration

### Access Control
- **JWT Authentication**: All external API access requires valid JWT tokens
- **Role-Based Access**: Admin functions are restricted to authenticated users
- **Audit Logging**: All conversation operations are logged for monitoring

## Monitoring & Maintenance

### Health Checks
- **Storage Status**: Monitor Redis connection and storage health
- **Conversation Counts**: Track active conversations and message counts
- **Cleanup Operations**: Monitor automatic cleanup processes

### Performance Metrics
- **Response Times**: Track AI processing performance
- **Memory Usage**: Monitor conversation storage memory consumption
- **Storage Efficiency**: Track Redis storage utilization

## Future Enhancements

### Planned Features
- **Database Integration**: PostgreSQL support for long-term storage
- **Encryption**: End-to-end encryption for sensitive conversations
- **Backup & Recovery**: Automated backup and recovery procedures
- **Analytics**: Conversation analytics and insights (anonymized)

### Scalability Improvements
- **Sharding**: Distribute conversations across multiple storage instances
- **Caching**: Multi-level caching for improved performance
- **Async Processing**: Background processing for conversation maintenance

## Troubleshooting

### Common Issues
1. **Redis Connection Failures**: System automatically falls back to in-memory
2. **Memory Issues**: Automatic cleanup prevents memory exhaustion
3. **Context Loss**: Conversations are automatically recreated if corrupted

### Debug Information
- **Logging**: Comprehensive logging for all conversation operations
- **Health Endpoints**: `/health` endpoint provides system status
- **Statistics**: `/api/ai/conversations/stats` shows conversation metrics

## Best Practices

### Development
- Use in-memory storage for local development
- Test conversation flows with various message patterns
- Monitor memory usage during development

### Production
- Configure Redis for persistent storage
- Set appropriate TTL values for your use case
- Monitor conversation statistics and cleanup operations
- Implement proper backup and recovery procedures

This conversation history system provides a robust foundation for maintaining AI chat context while ensuring user privacy and system performance.
