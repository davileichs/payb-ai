# Integration Tests

This directory contains integration tests for the Slack Bot AI Chat application.

## Overview

The integration tests verify that all components of the system work correctly together through Docker containers. These tests are designed to be run by DevOps teams to validate the system before deployment.

## Test Coverage

The integration tests verify:

1. **Health Check**: Application is running and healthy
2. **LLM Response**: AI providers (OpenAI/Ollama) are responding correctly
3. **Provider Switching**: Ability to switch between AI providers
4. **Weather Functionality**: Weather tool integration works
5. **Agent Recognition**: AI agent correctly identifies as "payb.ai"
6. **Configuration Reload**: Live reload of agents.json works

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured with proper API keys
- Python 3.11+ installed
- `requests` library installed (`pip install requests`)

## Running Tests

### Option 1: Automatic Docker Management (Recommended for CI/CD)

```bash
# Run integration tests with automatic Docker management
make integration-test
```

### Option 2: Manual Docker Control (Recommended for DevOps)

```bash
# Start Docker containers manually
make docker-run

# Run integration tests (containers must be running)
make integration-test-manual
# OR
./tests/run_integration_test.sh

# Stop Docker containers when done
make docker-stop
```

### Option 3: Direct Script Execution

```bash
# Start Docker containers
make docker-run

# Wait for containers to start (about 20-30 seconds)
sleep 20

# Run the integration test directly
python3 tests/integration_test.py

# Stop Docker containers
make docker-stop
```

## Configuration

The integration test automatically reads configuration from:

1. **Environment Variables**: `PORT`, `HOST`, `JWT_SECRET_KEY`
2. **`.env` File**: Falls back to reading from `.env` file if environment variables are not set

### Required Environment Variables

- `PORT`: Application port (default: 8000)
- `HOST`: Application host (default: localhost)
- `JWT_SECRET_KEY`: Authentication token for API calls

## Test Flow

1. **Health Check**: Verifies the application is running
2. **Initial LLM Test**: Tests basic AI response capability
3. **Provider Testing**: 
   - Tests current provider
   - Switches to alternative provider
   - Tests both providers for all functionality
4. **Weather Test**: Asks for weather in Frankfurt for both providers
5. **Name Recognition**: Asks "What is your name?" to verify agent identity
6. **Reload Test**: Tests live configuration reload functionality

## Expected Results

All tests should pass with:
- ✅ LLM responses containing expected content
- ✅ Provider switching working correctly
- ✅ Weather information returned for Frankfurt
- ✅ Agent identifying as "payb.ai"
- ✅ Configuration reload working

## Troubleshooting

### Common Issues

1. **Connection Refused**: 
   - Ensure Docker containers are running
   - Check if port 8000 is available
   - Verify `.env` file has correct HOST/PORT settings

2. **Authentication Failed**:
   - Check `JWT_SECRET_KEY` in `.env` file
   - Ensure the key matches the application configuration

3. **LLM Response Failures**:
   - Verify API keys are set in `.env` file
   - Check if OpenAI/Ollama services are accessible
   - Ensure sufficient API credits/quota

4. **Weather Test Failures**:
   - Check if `OPEN_WEATHER_KEY` is set in `.env` file
   - Verify internet connectivity for weather API calls

### Debug Mode

To run tests with more verbose output:

```bash
# Set debug environment variable
export DEBUG=true
python3 tests/integration_test.py
```

## Test Results

The test outputs:
- Real-time status of each test
- Detailed results with response data
- Summary with pass/fail counts
- Exit code: 0 for success, 1 for failure

## Integration with CI/CD

This test can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Integration Tests
  run: |
    make integration-test
```

## Manual DevOps Usage

For manual testing by DevOps teams:

1. Ensure all prerequisites are met
2. Run `./tests/run_integration_test.sh`
3. Review the test output
4. Check exit code (0 = success, 1 = failure)
5. Investigate any failed tests

The test is designed to be self-contained and provide clear feedback on system health.
