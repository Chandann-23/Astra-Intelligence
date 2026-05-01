# Astra Engine Production Deployment Guide

## 🎯 Cloud-Native Configuration Complete

The Astra Engine now supports both local development with LiteLLM proxy and production deployment with direct provider access.

## Hugging Face Secrets Configuration

### Required Secrets for Production

1. **GOOGLE_API_KEY**
   - Your Google Gemini API key
   - Required for primary LLM access
   - Get from: https://console.cloud.google.com/

2. **HUGGINGFACE_TOKEN**
   - Your Hugging Face API token
   - Required for fallback model access
   - Get from: https://huggingface.co/settings/tokens

3. **NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD**
   - Neo4j database credentials
   - Required for knowledge graph storage

4. **TAVILY_API_KEY**
   - Tavily search API key
   - Required for web search capabilities

5. **HF_TOKEN**
   - Hugging Face token for embeddings
   - Required for vector search

### Optional Secrets

- **OPENAI_BASE_URL**: Leave blank or unset for production
- **LITELLM_MASTER_KEY**: Not required for production (direct access)
- **ENVIRONMENT**: Set to "production" or leave unset

## How It Works

### Local Development
- Uses LiteLLM proxy on `http://localhost:48583`
- Automatic fallback between Gemini and Mistral
- Admin UI available at `http://localhost:48583/ui`

### Production (Hugging Face)
- Direct provider access (no proxy needed)
- Uses Gemini as primary model
- Falls back to Hugging Face if needed
- No localhost dependencies

## Deployment Steps

1. **Update Hugging Face Secrets**
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   HUGGINGFACE_TOKEN=your_hf_token_here
   NEO4J_URI=neo4j+s://your-neo4j-uri
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   TAVILY_API_KEY=your_tavily_api_key
   HF_TOKEN=your_hf_token_here
   ```

2. **Deploy to Hugging Face**
   ```bash
   git push staging-v2 main
   ```

3. **Verify Deployment**
   - Check: https://huggingface.co/spaces/Chandann-23/astra-backend-v2
   - Health endpoint: `/health`
   - Test with research query

## Expected Behavior

### Production Health Check Response
```json
{
  "status": "online",
  "services": {
    "neo4j": "connected",
    "gateway": "direct",
    "google": "configured",
    "huggingface": "configured",
    "tavily": "configured"
  }
}
```

### Research Request Flow
1. Frontend sends request to Hugging Face backend
2. Backend uses direct Gemini API access
3. Falls back to Hugging Face if needed
4. Stores results in Neo4j
5. Streams response back to frontend

## Troubleshooting

### Connection Errors
- Check all API keys are correctly set
- Verify Neo4j credentials are valid
- Ensure Tavily API key is active

### Authentication Errors
- Verify GOOGLE_API_KEY is valid
- Check HUGGINGFACE_TOKEN has proper permissions
- Ensure API keys have required quotas

### Performance Issues
- Monitor API usage quotas
- Check Neo4j connection limits
- Verify Tavily rate limits

## Benefits

✅ **Cloud-Native**: No localhost dependencies
✅ **Direct Access**: Faster response times
✅ **Automatic Fallback**: Built-in reliability
✅ **Production Ready**: Scalable architecture
✅ **Cost Optimized**: No proxy overhead

The Astra Engine is now production-ready for Hugging Face deployment! 🚀
