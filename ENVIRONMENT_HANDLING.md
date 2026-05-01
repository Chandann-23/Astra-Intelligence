# Astra Engine Environment Handling Guide

## 🎯 Enterprise-Grade Environment Configuration

This guide demonstrates the critical difference between local development and production deployment - a key skill for enterprise environments like IBM and Cognizant.

## Environment Detection Logic

### Local Development Environment
```python
# Detection
is_local = os.getenv("ENVIRONMENT") == "local" or os.getenv("OPENAI_BASE_URL", "").startswith("http://localhost")

# Configuration
if is_local:
    # Use LiteLLM proxy for development
    model = "openai/astra-brain"
    base_url = "http://localhost:48583/v1"
    api_key = os.getenv("LITELLM_MASTER_KEY")
```

### Production Environment (Hugging Face)
```python
# Production - Direct provider access
else:
    # Use Gemini directly through LiteLLM
    model = "gemini/gemini-1.5-flash"
    api_key = os.getenv("GOOGLE_API_KEY")
    # Note: No base_url - LiteLLM handles it automatically
```

## Why This Matters for Enterprise

### 1. **Dependency Management**
- **Local**: Uses proxy for testing and development
- **Production**: Direct access for reliability and performance
- **Enterprise Value**: Shows understanding of environment-specific dependencies

### 2. **Security Considerations**
- **Local**: Master key for proxy management
- **Production**: Direct API keys with proper access controls
- **Enterprise Value**: Demonstrates security-aware deployment practices

### 3. **Scalability**
- **Local**: Single proxy instance for development
- **Production**: Direct provider access for horizontal scaling
- **Enterprise Value**: Understanding of scalable architecture patterns

## LiteLLM Provider Configuration

### Gemini Provider (Production)
```yaml
# config.yaml - Local proxy configuration
model_list:
  - model_name: astra-brain
    litellm_params:
      model: gemini/gemini-1.5-flash
      api_base: "https://generativelanguage.googleapis.com/v1"
      api_key: os.environ/GOOGLE_API_KEY
```

### Direct Access (Production)
```python
# Production code - Let LiteLLM handle the endpoint
response = litellm.completion(
    model="gemini/gemini-1.5-flash",
    messages=[{"role": "user", "content": prompt}],
    api_key=os.getenv("GOOGLE_API_KEY")
    # No base_url needed - LiteLLM handles it
)
```

## Smart Fallback Strategy

### Local Fallback
```python
if is_local:
    # Try direct Gemini if proxy fails
    response = litellm.completion(
        model="gemini/gemini-1.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY")
    )
```

### Production Fallback
```python
else:
    # Try Hugging Face if Gemini fails
    response = litellm.completion(
        model="huggingface/mistral-7b-instruct",
        api_key=os.getenv("HUGGINGFACE_TOKEN")
    )
```

## Health Check Differences

### Local Health Check
```json
{
  "status": "online",
  "services": {
    "gateway": "proxy_online",
    "neo4j": "connected"
  }
}
```

### Production Health Check
```json
{
  "status": "online",
  "services": {
    "gateway": "direct_provider",
    "neo4j": "connected"
  }
}
```

## Enterprise Interview Talking Points

### 1. Environment-Aware Architecture
"Our Astra Engine uses environment-aware configuration to seamlessly transition between local development with proxy testing and production deployment with direct provider access."

### 2. Dependency Isolation
"We isolate environment-specific dependencies, ensuring that local development tools don't impact production reliability."

### 3. Smart Fallback Mechanisms
"Our system implements intelligent fallback strategies that adapt to the environment - local environments fallback to direct APIs, while production environments fallback to alternative providers."

### 4. Security by Design
"We implement security-conscious key management, using master keys for local development and direct API keys for production with proper access controls."

## Configuration Checklist

### Local Development
- [x] Set `ENVIRONMENT=local`
- [x] Set `LITELLM_MASTER_KEY`
- [x] Set `GOOGLE_API_KEY`
- [x] Start LiteLLM proxy on port 48583

### Production (Hugging Face)
- [x] Unset or remove `OPENAI_BASE_URL`
- [x] Set `GOOGLE_API_KEY`
- [x] Set `HUGGINGFACE_TOKEN`
- [x] Set Neo4j credentials
- [x] Set `TAVILY_API_KEY`

## Testing Strategy

### Local Testing
```bash
# Set environment
export ENVIRONMENT=local
export LITELLM_MASTER_KEY="your_key"

# Test with proxy
curl http://localhost:8002/health
# Expected: gateway: "proxy_online"
```

### Production Testing
```bash
# Production (Hugging Face)
# No ENVIRONMENT variable set
curl https://your-space.hf.space/health
# Expected: gateway: "direct_provider"
```

This environment-aware configuration demonstrates enterprise-grade development practices that are highly valued at companies like IBM, Cognizant, and other enterprise organizations.
