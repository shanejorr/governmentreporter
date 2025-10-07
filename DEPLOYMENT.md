# GovernmentReporter Deployment Guide

This guide covers deploying GovernmentReporter in production environments using Docker, cloud platforms, or direct installation.

## Table of Contents

- [Quick Start with Docker](#quick-start-with-docker)
- [Prerequisites](#prerequisites)
- [Local Development Deployment](#local-development-deployment)
- [Production Deployment](#production-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Configuration](#configuration)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

---

## Quick Start with Docker

The fastest way to deploy GovernmentReporter is using Docker Compose:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/governmentreporter.git
cd governmentreporter

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env and add your API keys
nano .env  # or your preferred editor

# 4. Start all services
docker-compose up -d

# 5. Verify services are running
docker-compose ps

# 6. View logs
docker-compose logs -f mcp-server
```

Your MCP server is now running and connected to a Qdrant vector database!

---

## Prerequisites

### Required

- **Docker** 20.10+ and **Docker Compose** 1.29+ (for containerized deployment)
- **Python** 3.11+ (for direct installation)
- **OpenAI API Key** (for embeddings and document-level metadata extraction)
- **CourtListener API Token** (for SCOTUS ingestion only)

### Storage Requirements

- **Qdrant Database**: ~1-5 GB per 10,000 documents (depends on embedding size)
- **Progress Tracking**: Minimal (<100 MB)
- **Logs**: Configure rotation; typically <500 MB

### Network Requirements

- **Outbound HTTPS** to:
  - OpenAI API (`api.openai.com`)
  - CourtListener (`www.courtlistener.com`)
  - Federal Register (`www.federalregister.gov`)

---

## Local Development Deployment

### Method 1: Using uv (Recommended)

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start Qdrant locally (Docker)
docker run -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant

# Start MCP server
uv run governmentreporter server
```

### Method 2: Using pip

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start Qdrant
docker run -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant

# Start MCP server
governmentreporter server
```

---

## Production Deployment

### Docker Compose (Production Ready)

```bash
# 1. Prepare environment
cp .env.example .env
nano .env  # Add production API keys and settings

# 2. Create necessary directories
mkdir -p data/qdrant data/progress logs

# 3. Configure logging
cp logging.yaml logging.prod.yaml
# Edit logging.prod.yaml for production log levels

# 4. Build and start services
docker-compose up -d

# 5. Monitor logs
docker-compose logs -f mcp-server

# 6. Health check
docker-compose ps
curl http://localhost:6333/health  # Qdrant health
```

**Note**: For document ingestion, use the CLI with `uv` locally or set up GitHub Actions for scheduled ingestion. See the main README for ingestion instructions.

### Systemd Service (Linux)

For running without Docker on Linux servers:

```bash
# Create systemd service file
sudo nano /etc/systemd/system/governmentreporter.service
```

```ini
[Unit]
Description=GovernmentReporter MCP Server
After=network.target

[Service]
Type=simple
User=mcpserver
Group=mcpserver
WorkingDirectory=/opt/governmentreporter
Environment="PATH=/opt/governmentreporter/.venv/bin"
EnvironmentFile=/opt/governmentreporter/.env
ExecStart=/opt/governmentreporter/.venv/bin/python -m governmentreporter.server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable governmentreporter
sudo systemctl start governmentreporter

# Check status
sudo systemctl status governmentreporter

# View logs
sudo journalctl -u governmentreporter -f
```

---

## Cloud Deployment

### AWS Deployment

#### Option 1: ECS with Fargate

```bash
# 1. Build and push Docker image to ECR
aws ecr create-repository --repository-name governmentreporter
docker build -t governmentreporter .
docker tag governmentreporter:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/governmentreporter:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/governmentreporter:latest

# 2. Create ECS task definition (see aws-ecs-task-definition.json)
aws ecs register-task-definition --cli-input-json file://aws-ecs-task-definition.json

# 3. Create ECS service
aws ecs create-service --cluster governmentreporter-cluster \
  --service-name mcp-server \
  --task-definition governmentreporter:1 \
  --desired-count 1 \
  --launch-type FARGATE
```

#### Option 2: EC2 with Docker

```bash
# Launch EC2 instance (Ubuntu 22.04)
# SSH into instance and run:
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
# Logout and login again

# Clone repository
git clone https://github.com/yourusername/governmentreporter.git
cd governmentreporter

# Configure and start
cp .env.example .env
nano .env  # Add API keys
docker-compose up -d
```

### Google Cloud Platform

```bash
# 1. Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT-ID/governmentreporter

# 2. Deploy to Cloud Run
gcloud run deploy governmentreporter \
  --image gcr.io/PROJECT-ID/governmentreporter \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY \
  --set-env-vars QDRANT_HOST=your-qdrant-instance \
  --allow-unauthenticated
```

### Azure

```bash
# 1. Create Azure Container Instance
az container create \
  --resource-group governmentreporter-rg \
  --name governmentreporter-mcp \
  --image yourusername/governmentreporter:latest \
  --environment-variables \
    OPENAI_API_KEY=$OPENAI_API_KEY \
    QDRANT_HOST=your-qdrant-host \
  --ports 8080
```

---

## Configuration

### Environment Variables

Key configuration variables (see `.env.example` for full list):

```bash
# Required
OPENAI_API_KEY=sk-...
COURT_LISTENER_API_TOKEN=...

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_DB_PATH=./data/qdrant/qdrant_db

# MCP Server
MCP_SERVER_NAME=GovernmentReporter
MCP_LOG_LEVEL=INFO
MCP_DEFAULT_SEARCH_LIMIT=10
```

### Logging Configuration

Edit `logging.yaml` to customize logging behavior:

```yaml
# Change log levels
loggers:
  governmentreporter.server:
    level: DEBUG  # DEBUG, INFO, WARNING, ERROR

# Change log file locations
handlers:
  file:
    filename: /var/log/governmentreporter/app.log
```

### Performance Tuning

#### Ingestion Performance

```bash
# Increase batch size for faster ingestion
SCOTUS_BATCH_SIZE=100  # Default: 50
EO_BATCH_SIZE=100      # Default: 50

# Adjust chunking parameters
RAG_SCOTUS_TARGET_TOKENS=500  # Smaller = faster
```

#### Server Performance

```bash
# Adjust search limits
MCP_DEFAULT_SEARCH_LIMIT=5   # Faster response
MCP_MAX_SEARCH_LIMIT=25      # Limit max results

# Enable caching
MCP_ENABLE_CACHE=true
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# Check Qdrant health
curl http://localhost:6333/health

# Check MCP server logs
docker-compose logs -f mcp-server

# Monitor resource usage
docker stats governmentreporter-mcp
```

### Log Management

```bash
# View application logs
tail -f logs/governmentreporter.log

# View error logs only
tail -f logs/errors.log

# View ingestion progress
tail -f logs/ingestion.log

# Rotate logs manually
logrotate -f /etc/logrotate.d/governmentreporter
```

### Database Backup

```bash
# Backup Qdrant database
docker exec governmentreporter-qdrant tar czf /backup/qdrant-$(date +%Y%m%d).tar.gz /qdrant/storage

# Backup progress databases
tar czf backups/progress-$(date +%Y%m%d).tar.gz data/progress/
```

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify update
docker-compose logs -f mcp-server
```

---

## Troubleshooting

### Common Issues

#### 1. MCP Server Won't Start

**Symptom**: Container exits immediately or fails to start

**Solutions**:
```bash
# Check logs
docker-compose logs mcp-server

# Verify environment variables
docker-compose config

# Check Qdrant connection
docker-compose exec mcp-server curl http://qdrant:6333/health
```

#### 2. Ingestion Fails

**Symptom**: Documents not being ingested or errors in logs

**Solutions**:
```bash
# Check API keys
echo $OPENAI_API_KEY  # Should not be empty

# Verify API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check progress database
sqlite3 data/progress/scotus_ingestion.db "SELECT COUNT(*) FROM documents;"

# Resume failed ingestion using uv
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31
```

#### 3. Qdrant Connection Issues

**Symptom**: "Connection refused" or timeouts

**Solutions**:
```bash
# Verify Qdrant is running
docker-compose ps qdrant

# Check Qdrant logs
docker-compose logs qdrant

# Test connection from host
curl http://localhost:6333/health

# Test connection from container
docker-compose exec mcp-server curl http://qdrant:6333/health
```

#### 4. Out of Memory

**Symptom**: Container killed or slow performance

**Solutions**:
```bash
# Increase Docker memory limit for MCP server
# Edit docker-compose.yml and add:
services:
  mcp-server:
    mem_limit: 4g

# Monitor memory usage
docker stats
```

#### 5. Search Returns No Results

**Symptom**: MCP tools return empty results

**Solutions**:
```bash
# Verify data was ingested
docker-compose exec qdrant curl http://localhost:6333/collections

# Check collection statistics
uv run governmentreporter query "test"

# Re-index if needed
uv run governmentreporter ingest scotus --start-date 2024-01-01 --end-date 2024-12-31
uv run governmentreporter ingest eo --start-date 2024-01-01 --end-date 2024-12-31
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Set environment variable
MCP_LOG_LEVEL=DEBUG

# Restart service
docker-compose restart mcp-server

# Watch debug logs
docker-compose logs -f mcp-server | grep DEBUG
```

### Getting Help

- **Issues**: https://github.com/yourusername/governmentreporter/issues
- **Discussions**: https://github.com/yourusername/governmentreporter/discussions
- **Email**: support@governmentreporter.example

---

## Security Considerations

### Production Security Checklist

- [ ] Use strong, unique API keys
- [ ] Never commit `.env` file to version control
- [ ] Run containers as non-root user (already configured in Dockerfile)
- [ ] Enable firewall rules to restrict Qdrant access
- [ ] Use HTTPS/TLS for external API calls
- [ ] Rotate API keys periodically
- [ ] Monitor logs for suspicious activity
- [ ] Keep Docker images and dependencies updated
- [ ] Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Enable audit logging
- [ ] Backup databases regularly

### Network Security

```bash
# Restrict Qdrant to internal network only
# In docker-compose.yml:
services:
  qdrant:
    networks:
      - internal
    # Remove ports section to prevent external access

networks:
  internal:
    internal: true
```

---

## Performance Benchmarks

Typical performance metrics:

- **Ingestion**: 50-100 documents/minute (depends on API limits)
- **Search Latency**: <500ms for semantic search
- **Concurrent Searches**: 10-20 per second per core
- **Memory**: 1-2 GB base + ~1 MB per 1000 indexed chunks
- **CPU**: Minimal (<10%) during search, 50-80% during ingestion

---

## Next Steps

After deployment:

1. **Integrate with Claude Desktop** - See Claude Desktop Integration Tutorial in README.md
2. **Schedule Regular Ingestion** - Set up cron jobs or scheduled tasks
3. **Monitor Performance** - Set up metrics collection (Prometheus, Grafana)
4. **Configure Alerts** - Set up notifications for errors or failures
5. **Scale as Needed** - Add more replicas for high-traffic scenarios

Happy deploying! 🚀
