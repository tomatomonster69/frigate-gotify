# Frigate-Gotify

A lightweight Docker notification service that bridges Frigate NVR review events to Gotify push notifications with embedded snapshot images.

## Features

- **Review Event Monitoring**: Polls Frigate API for new review events
- **GenAI Descriptions**: Includes Frigate's GenAI-generated descriptions in notifications
- **Embedded Images**: Snapshots are sent as base64-encoded images, allowing remote clients to view them without access to the local network
- **SSL-Free Operation**: Works entirely over HTTP on local network, avoiding SSL certificate issues
- **Configurable Filtering**: Filter by severity level and cameras
- **Lightweight**: Minimal dependencies, runs in a small container

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Frigate NVR   │──────▶  frigate-gotify  │──────▶     Gotify      │
│  (http:5000)    │      │    (Docker)      │      │   (http:80)     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  Mobile Client  │
                                                  │    (Remote)     │
                                                  └─────────────────┘
```

## Requirements

- Frigate NVR with GenAI enabled
- Gotify server (running locally)
- Docker and docker-compose

## Quick Start

### 1. Clone/Download the Project

```bash
cd /path/to/frigate-gotify
```

### 2. Create Configuration File

```bash
cp .env.example .env
```

Edit `.env` and configure:
- `FRIGATE_URL` - URL of your Frigate server (e.g., `http://frigate:5000`)
- `GOTIFY_URL` - URL of your Gotify server (e.g., `http://gotify-server:80`)
- `GOTIFY_APP_TOKEN` - Application token from Gotify

### 3. Create Gotify Application

1. Open your Gotify web UI
2. Go to **Applications** → **Create Application**
3. Name it "Frigate" or similar
4. Copy the application token to your `.env` file

### 4. Create Docker Network (if needed)

If Frigate is running in Docker, ensure this service can reach it:

```bash
docker network create frigate-network
```

Or update `docker-compose.yml` to use the same network as your Frigate container.

### 5. Build and Run

```bash
docker-compose up -d --build
```

### 6. Check Logs

```bash
docker-compose logs -f
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FRIGATE_URL` | `http://frigate:5000` | Frigate NVR URL |
| `FRIGATE_USERNAME` | - | Username for Frigate auth (optional) |
| `FRIGATE_PASSWORD` | - | Password for Frigate auth (optional) |
| `FRIGATE_API_KEY` | - | API key for Frigate (optional) |
| `GOTIFY_URL` | *required* | Gotify server URL |
| `GOTIFY_APP_TOKEN` | *required* | Gotify application token |
| `VERIFY_SSL` | `false` | Verify SSL certificates |
| `POLL_INTERVAL` | `10` | Polling interval in seconds |
| `NOTIFICATION_PRIORITY` | `5` | Default notification priority (1-10) |
| `INCLUDE_SNAPSHOT` | `true` | Include snapshot images |
| `SEVERITY_FILTER` | `alert,detection` | Severity levels to notify |
| `CAMERA_FILTER` | `all` | Cameras to monitor (comma-separated) |
| `DEBUG` | `false` | Enable debug logging |

## How It Works

1. **Polling Loop**: The service polls Frigate's `/api/review` endpoint every `POLL_INTERVAL` seconds
2. **Event Detection**: New unreviewed events are detected and processed
3. **Data Collection**: For each review event:
   - Fetches related events to find GenAI descriptions
   - Downloads the snapshot image
4. **Notification**: Sends a Gotify notification with:
   - Title with severity and camera name
   - GenAI description (if available)
   - Detected objects, zones, and audio
   - Timestamp
   - Embedded snapshot image (base64)

## Image Embedding

The key feature is embedding images as base64 data URIs. This ensures:

- Remote mobile clients can view images without VPN or local network access
- No dependency on reverse proxy or external URLs
- Images are self-contained in the notification

## Troubleshooting

### Enable Debug Logging

```env
DEBUG=true
```

### Check Frigate Connectivity

```bash
docker exec frigate-gotify python -c "
import httpx
resp = httpx.get('http://frigate:5000/api/stats')
print(resp.status_code)
"
```

### Check Gotify Connectivity

```bash
docker exec frigate-gotify python -c "
import httpx
resp = httpx.get('http://gotify-server:80/health')
print(resp.status_code)
"
```

### Common Issues

1. **Cannot connect to Frigate**: Ensure both containers are on the same Docker network
2. **Notifications not sending**: Check that `GOTIFY_APP_TOKEN` is correct
3. **No images in notifications**: Set `INCLUDE_SNAPSHOT=true` and check Frigate has snapshots

## Development

### Run Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env

# Run
python -m src.main
```

### Project Structure

```
frigate-gotify/
├── src/
│   ├── __init__.py        # Package exports
│   ├── config.py          # Configuration management
│   ├── frigate_client.py  # Frigate API client
│   ├── gotify_client.py   # Gotify API client
│   └── main.py            # Main service loop
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT License