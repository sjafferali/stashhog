# FFmpeg Requirement

## Overview

StashHog requires FFmpeg (specifically `ffprobe`) to analyze video durations in the Process Downloads job. This is used to detect and optionally skip video files that are under 30 seconds in duration.

## Docker Installation

FFmpeg is automatically installed in both production and development Docker images:

- **Production** (`Dockerfile`): Installed in the final production stage
- **Development** (`backend/Dockerfile.dev`): Installed for local development

## Local Development (Without Docker)

If running the backend directly on your local machine, you need to install FFmpeg:

### macOS
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### CentOS/RHEL/Fedora
```bash
sudo yum install ffmpeg
```

### Windows
Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH.

## Verification

### In Docker
After building your Docker images, verify FFmpeg is available:

```bash
# Run the verification script
./scripts/verify-ffmpeg.sh

# Or manually check
docker compose exec backend ffmpeg -version
docker compose exec backend ffprobe -version
```

### Local Installation
```bash
ffmpeg -version
ffprobe -version
```

## Usage in Process Downloads

The Process Downloads job uses `ffprobe` to:

1. Detect video file durations
2. Track files under 30 seconds
3. Optionally skip short videos when `exclude_small_vids` flag is enabled

### Features

- **Video Detection**: Identifies video files by extension (.mp4, .avi, .mkv, etc.)
- **Duration Check**: Uses `ffprobe` to get accurate video duration
- **Graceful Handling**: If `ffprobe` fails, the file is still processed normally
- **Statistics Tracking**: Always reports count of files under 30 seconds

### Job Parameters

When running Process Downloads or Process New Scenes jobs, you can enable the `exclude_small_vids` flag to skip videos under 30 seconds.

## Troubleshooting

### FFmpeg Not Found
If you see errors about ffmpeg/ffprobe not being found:

1. **In Docker**: Rebuild your images
   ```bash
   docker compose build --no-cache backend
   ```

2. **Local**: Ensure FFmpeg is in your PATH
   ```bash
   which ffmpeg
   which ffprobe
   ```

### Permission Issues
Ensure the user running the backend has execute permissions for ffmpeg/ffprobe.

### Performance Considerations
- `ffprobe` is fast and lightweight
- Only analyzes video files (checks extension first)
- Timeout of 10 seconds per file to prevent hanging
- Failures don't stop the job from processing