# StashHog Settings Documentation

This document provides a comprehensive overview of all configuration settings available in StashHog, including environment variables and UI-configurable settings.

## Environment Variables

StashHog uses environment variables for configuration that should be set before the application starts. These variables use a nested delimiter (`__`) for complex settings.

### Application Settings (`APP_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `StashHog` | Application name displayed in the UI |
| `APP_VERSION` | `0.1.0` | Application version |
| `APP_DEBUG` | `false` | Enable debug mode (should be `false` in production) |
| `APP_ENVIRONMENT` | `production` | Environment type (`development`, `staging`, `production`) |

### Database Settings (`DATABASE_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./stashhog.db` | Database connection URL (SQLite by default) |
| `DATABASE_ECHO` | `false` | Echo SQL statements to logs (useful for debugging) |
| `DATABASE_POOL_SIZE` | `10` | Number of connections in the database pool |
| `DATABASE_POOL_RECYCLE` | `3600` | Time in seconds to recycle database connections |

### Stash Integration Settings (`STASH_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `STASH_URL` | `http://localhost:9999` | URL of your Stash server |
| `STASH_API_KEY` | `None` | API key for Stash authentication (optional if not required) |
| `STASH_TIMEOUT` | `30` | Request timeout in seconds |
| `STASH_MAX_RETRIES` | `3` | Maximum number of retry attempts for failed requests |
| `STASH_PREVIEW_PRESET` | `ultrafast` | Video encoding preset for preview generation (ultrafast, veryfast, fast, medium, slow, slower, veryslow) |

### OpenAI Settings (`OPENAI_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `None` | OpenAI API key for AI-powered features |
| `OPENAI_MODEL` | `gpt-4` | AI model to use for analysis |
| `OPENAI_MAX_TOKENS` | `2000` | Maximum tokens per AI request |
| `OPENAI_TEMPERATURE` | `0.7` | Temperature for AI generation (0.0-2.0) |
| `OPENAI_TIMEOUT` | `60` | API request timeout in seconds |

### Security Settings (`SECURITY_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECURITY_SECRET_KEY` | `change-this-in-production-to-a-random-string` | Secret key for signing tokens (⚠️ MUST be changed in production) |
| `SECURITY_ALGORITHM` | `HS256` | JWT signing algorithm |
| `SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token expiration time in minutes |

### CORS Settings (`CORS_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000", "http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `CORS_CREDENTIALS` | `true` | Allow credentials in CORS requests |
| `CORS_METHODS` | `["*"]` | Allowed HTTP methods |
| `CORS_HEADERS` | `["*"]` | Allowed headers |

### Logging Settings (`LOGGING_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOGGING_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOGGING_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Log message format |
| `LOGGING_JSON_LOGS` | `false` | Use JSON format for logs |

### Analysis Settings (`ANALYSIS_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYSIS_BATCH_SIZE` | `15` | Number of scenes to analyze per batch |
| `ANALYSIS_MAX_CONCURRENT` | `3` | Maximum concurrent analysis batches |
| `ANALYSIS_CONFIDENCE_THRESHOLD` | `0.7` | Default confidence threshold for AI detections |
| `ANALYSIS_ENABLE_AI` | `true` | Enable AI-based detection features |
| `ANALYSIS_CREATE_MISSING` | `false` | Automatically create missing entities during analysis |

### General Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `None` | Redis connection URL (optional, for future caching) |
| `MAX_WORKERS` | `5` | Maximum number of background worker threads |
| `TASK_TIMEOUT` | `300` | Default task timeout in seconds |

## UI-Configurable Settings

These settings can be modified through the application's Settings page and are stored in the database.

### Stash Configuration

| Setting | Type | Description |
|---------|------|-------------|
| `stash_url` | String | URL of your Stash server |
| `stash_api_key` | String (sensitive) | API key for Stash authentication |
| `stash_preview_preset` | Select | Video encoding preset for preview generation (ultrafast to veryslow) |

**Features:**
- Test Connection button to verify Stash connectivity
- Settings marked as sensitive are masked in the UI

### OpenAI Configuration

| Setting | Type | Description |
|---------|------|-------------|
| `openai_api_key` | String (sensitive) | OpenAI API key |
| `openai_model` | Select | AI model selection (GPT-4, GPT-3.5 Turbo) |
| `openai_temperature` | Number (0-2) | Temperature for AI generation |
| `openai_max_tokens` | Number (1-4000) | Maximum tokens per request |

**Features:**
- Test Connection button to verify OpenAI API access
- Model availability check

### Analysis Settings

| Setting | Type | Description |
|---------|------|-------------|
| `analysis_confidence_threshold` | Number (0-1) | Confidence threshold for AI detections |
| `analysis_batch_size` | Number | Scenes per analysis batch (affects performance) |

### Sync Settings

| Setting | Type | Description |
|---------|------|-------------|
| `sync_incremental` | Boolean | Enable incremental sync (only sync changes) |
| `sync_batch_size` | Number | Number of items to sync per batch |

### General Settings

| Setting | Type | Description |
|---------|------|-------------|
| `auto_analyze_new_scenes` | Boolean | Automatically analyze newly synced scenes |
| `enable_websocket_notifications` | Boolean | Enable real-time notifications |
| `log_level` | Select | Application log level (Debug, Info, Warning, Error) |

## Settings Priority

Settings are loaded in the following priority order (highest to lowest):
1. Environment variables
2. Database-stored settings (from UI)
3. Default values in code

## Important Notes

### Preview Preset Usage

The `stash_preview_preset` setting controls the video encoding quality/speed tradeoff when generating previews in Stash:

- **ultrafast**: Lowest quality, fastest processing (recommended for quick testing)
- **veryfast/fast**: Good balance for development environments
- **medium**: Balanced quality and speed
- **slow/slower**: Higher quality, longer processing time
- **veryslow**: Highest quality, slowest processing (recommended for production archives)

This setting is used in:
- Stash metadata generation jobs (`stash_generate_job`)
- Process new scenes workflow (Step 5: Stash Generate Metadata)
- Any manual or scheduled preview generation tasks

### Security Considerations

1. **Secret Key**: The `SECURITY_SECRET_KEY` MUST be changed to a random string in production
2. **API Keys**: Store API keys securely and never commit them to version control
3. **CORS Origins**: In production, specify exact allowed origins instead of wildcards

### Performance Tuning

1. **Database Pool Size**: Increase for high-traffic deployments
2. **Analysis Batch Size**: Larger batches are more efficient but use more memory
3. **Max Concurrent**: Adjust based on available system resources
4. **Sync Batch Size**: Balance between memory usage and sync speed

### Restart Requirements

Some settings require an application restart to take effect:
- `stash_url`
- `stash_api_key`
- Database connection settings
- CORS configuration

The UI will indicate when a restart is required after changing settings.

## Example .env File

```env
# Application
APP_NAME=StashHog
APP_ENVIRONMENT=production
APP_DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@localhost/stashhog
DATABASE_POOL_SIZE=20

# Stash Integration
STASH_URL=http://your-stash-server:9999
STASH_API_KEY=your-stash-api-key

# OpenAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4

# Security (CHANGE THIS!)
SECURITY_SECRET_KEY=your-random-secret-key-here

# CORS (for production)
CORS_ORIGINS=["https://your-domain.com"]

# Analysis
ANALYSIS_BATCH_SIZE=20
ANALYSIS_MAX_CONCURRENT=5
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Check `DATABASE_URL` format and credentials
2. **Stash connection failures**: Verify `STASH_URL` is accessible and API key is correct
3. **OpenAI errors**: Ensure API key is valid and has sufficient credits
4. **CORS errors**: Add your frontend URL to `CORS_ORIGINS`

### Debug Mode

Enable debug mode for detailed error messages:
```env
APP_DEBUG=true
LOGGING_LEVEL=DEBUG
DATABASE_ECHO=true
```

⚠️ **Warning**: Never enable debug mode in production as it may expose sensitive information.