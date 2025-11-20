# Deployment Guide

This guide covers deploying refactor-mcp Python rewrite to various environments.

## Table of Contents

- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [FastMCP Cloud](#fastmcp-cloud)
- [Systemd Service](#systemd-service)
- [Cloud Platforms](#cloud-platforms)
- [Configuration](#configuration)
- [Monitoring](#monitoring)

## Docker Deployment

### Quick Start with Docker

```bash
# Build the image
cd python
docker build -t refactor-mcp:latest .

# Run with stdio transport
docker run -it --rm \
  -v $(pwd)/workspace:/workspace:rw \
  -e REFACTOR_MCP_ALLOWED_ROOT_PATHS=/workspace \
  refactor-mcp:latest

# Run with SSE transport (HTTP)
docker run -d \
  --name refactor-mcp \
  -p 8000:8000 \
  -v $(pwd)/workspace:/workspace:rw \
  -e REFACTOR_MCP_ALLOWED_ROOT_PATHS=/workspace \
  refactor-mcp:latest \
  python -m refactor_mcp.cli --transport sse --port 8000
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables

```bash
docker run -d \
  -e REFACTOR_MCP_ALLOWED_ROOT_PATHS="/workspace,/projects" \
  -e REFACTOR_MCP_LOG_LEVEL=DEBUG \
  -e REFACTOR_MCP_CACHE_MAX_SIZE_MB=2048 \
  -e REFACTOR_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE=200 \
  -e REFACTOR_MCP_GITHUB_CLIENT_ID=your_client_id \
  -e REFACTOR_MCP_GITHUB_CLIENT_SECRET=your_secret \
  refactor-mcp:latest
```

## Kubernetes Deployment

### Basic Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: refactor-mcp
  labels:
    app: refactor-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: refactor-mcp
  template:
    metadata:
      labels:
        app: refactor-mcp
    spec:
      containers:
      - name: refactor-mcp
        image: ghcr.io/yourusername/refactor-mcp:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: REFACTOR_MCP_ALLOWED_ROOT_PATHS
          value: "/workspace"
        - name: REFACTOR_MCP_LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "from refactor_mcp.config import Config; Config.load()"
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "from refactor_mcp.config import Config; Config.load()"
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: refactor-mcp-workspace
---
apiVersion: v1
kind: Service
metadata:
  name: refactor-mcp
spec:
  selector:
    app: refactor-mcp
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -l app=refactor-mcp
kubectl logs -f deployment/refactor-mcp
```

### ConfigMap for Configuration

Create `k8s-configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: refactor-mcp-config
data:
  REFACTOR_MCP_ALLOWED_ROOT_PATHS: "/workspace,/projects"
  REFACTOR_MCP_LOG_LEVEL: "INFO"
  REFACTOR_MCP_CACHE_MAX_SIZE_MB: "4096"
  REFACTOR_MCP_RATE_LIMIT_ENABLED: "true"
---
apiVersion: v1
kind: Secret
metadata:
  name: refactor-mcp-secrets
type: Opaque
stringData:
  REFACTOR_MCP_GITHUB_CLIENT_ID: "your_client_id"
  REFACTOR_MCP_GITHUB_CLIENT_SECRET: "your_secret"
```

Reference in deployment:

```yaml
envFrom:
- configMapRef:
    name: refactor-mcp-config
- secretRef:
    name: refactor-mcp-secrets
```

## FastMCP Cloud

FastMCP 2.0 provides one-line deployment to managed cloud infrastructure.

### Setup

```bash
# Install FastMCP CLI
pip install fastmcp[cloud]

# Login
fastmcp login

# Deploy
cd python
fastmcp deploy

# Check status
fastmcp status

# View logs
fastmcp logs

# Update deployment
fastmcp deploy --update
```

### Configuration

Create `.fastmcp/config.yaml`:

```yaml
name: refactor-mcp
version: 2.0.0
runtime: python3.11
entry_point: refactor_mcp.cli:main

environment:
  REFACTOR_MCP_ALLOWED_ROOT_PATHS: "/workspace"
  REFACTOR_MCP_LOG_LEVEL: "INFO"

resources:
  memory: 4096
  cpu: 2

scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 70

auth:
  providers:
    - github
    - google
```

## Systemd Service

For running on Linux servers.

Create `/etc/systemd/system/refactor-mcp.service`:

```ini
[Unit]
Description=Refactor MCP Server
After=network.target

[Service]
Type=simple
User=mcp
Group=mcp
WorkingDirectory=/opt/refactor-mcp/python
Environment="REFACTOR_MCP_ALLOWED_ROOT_PATHS=/home/mcp/projects"
Environment="REFACTOR_MCP_LOG_LEVEL=INFO"
ExecStart=/opt/refactor-mcp/venv/bin/python -m refactor_mcp.cli --transport sse --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable refactor-mcp
sudo systemctl start refactor-mcp
sudo systemctl status refactor-mcp

# View logs
sudo journalctl -u refactor-mcp -f
```

## Cloud Platforms

### AWS (ECS Fargate)

Create `task-definition.json`:

```json
{
  "family": "refactor-mcp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "refactor-mcp",
      "image": "ghcr.io/yourusername/refactor-mcp:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REFACTOR_MCP_ALLOWED_ROOT_PATHS",
          "value": "/workspace"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/refactor-mcp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Deploy:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service --cluster my-cluster --service-name refactor-mcp --task-definition refactor-mcp
```

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/refactor-mcp

# Deploy
gcloud run deploy refactor-mcp \
  --image gcr.io/PROJECT_ID/refactor-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars REFACTOR_MCP_ALLOWED_ROOT_PATHS=/workspace
```

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name refactor-mcp \
  --image ghcr.io/yourusername/refactor-mcp:latest \
  --dns-name-label refactor-mcp \
  --ports 8000 \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    REFACTOR_MCP_ALLOWED_ROOT_PATHS=/workspace \
    REFACTOR_MCP_LOG_LEVEL=INFO
```

## Configuration

### Environment Variables

All configuration can be set via environment variables with `REFACTOR_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `REFACTOR_MCP_ALLOWED_ROOT_PATHS` | `~/projects,/workspace` | Allowed root directories |
| `REFACTOR_MCP_LOG_LEVEL` | `INFO` | Logging level |
| `REFACTOR_MCP_CACHE_MAX_SIZE_MB` | `4096` | Cache size limit |
| `REFACTOR_MCP_ROSLYN_CLI_PATH` | Auto-detected | Path to Roslyn CLI |
| `REFACTOR_MCP_RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `REFACTOR_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE` | `100` | Request limit |
| `REFACTOR_MCP_ENABLE_METRICS` | `true` | Enable metrics |
| `REFACTOR_MCP_ENABLE_TRACING` | `true` | Enable tracing |

### Secrets Management

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name refactor-mcp/github-oauth \
  --secret-string '{"client_id":"xxx","client_secret":"yyy"}'
```

**Kubernetes Secrets:**
```bash
kubectl create secret generic refactor-mcp-oauth \
  --from-literal=github-client-id=xxx \
  --from-literal=github-client-secret=yyy
```

**Docker Secrets:**
```bash
echo "xxx" | docker secret create github_client_id -
echo "yyy" | docker secret create github_client_secret -
```

## Monitoring

### Metrics

FastMCP automatically exports metrics to Prometheus format at `/metrics`:

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'refactor-mcp'
    static_configs:
      - targets: ['refactor-mcp:8000']
    metrics_path: '/metrics'
```

Key metrics:
- `mcp_requests_total` - Total requests
- `mcp_request_duration_seconds` - Request latency
- `mcp_errors_total` - Error count
- `mcp_cache_hits_total` - Cache hit rate

### Logging

**ELK Stack:**
```yaml
logging:
  driver: "fluentd"
  options:
    fluentd-address: "localhost:24224"
    tag: "refactor-mcp"
```

**Datadog:**
```yaml
environment:
  DD_AGENT_HOST: "datadog-agent"
  DD_SERVICE: "refactor-mcp"
  DD_ENV: "production"
```

### Health Checks

The server exposes health check endpoints:

- `GET /health` - Overall health status
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics

## Scaling

### Horizontal Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: refactor-mcp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: refactor-mcp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Load Balancing

Use Nginx as reverse proxy:

```nginx
upstream refactor_mcp {
    least_conn;
    server refactor-mcp-1:8000;
    server refactor-mcp-2:8000;
    server refactor-mcp-3:8000;
}

server {
    listen 80;
    server_name refactor-mcp.example.com;

    location / {
        proxy_pass http://refactor_mcp;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Security

### TLS/SSL

Use Let's Encrypt with Cert-Manager (Kubernetes):

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: refactor-mcp-tls
spec:
  secretName: refactor-mcp-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - refactor-mcp.example.com
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: refactor-mcp-policy
spec:
  podSelector:
    matchLabels:
      app: refactor-mcp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: claude-desktop
    ports:
    - protocol: TCP
      port: 8000
```

## Troubleshooting

**Container won't start:**
```bash
docker logs refactor-mcp
kubectl describe pod refactor-mcp-xxx
```

**Roslyn CLI not found:**
```bash
# Verify Roslyn CLI is in image
docker run --rm --entrypoint ls refactor-mcp:latest /app/roslyn_cli/bin/
```

**Permission errors:**
```bash
# Check file permissions
docker run --rm --entrypoint ls refactor-mcp:latest -la /app
```

**High memory usage:**
```bash
# Reduce cache size
docker run -e REFACTOR_MCP_CACHE_MAX_SIZE_MB=1024 refactor-mcp:latest
```

## Best Practices

1. **Use specific image tags** instead of `latest` in production
2. **Set resource limits** to prevent resource exhaustion
3. **Enable health checks** for automatic recovery
4. **Use secrets management** for sensitive data
5. **Monitor logs and metrics** continuously
6. **Scale horizontally** for high availability
7. **Use TLS/SSL** for all external communication
8. **Implement rate limiting** to prevent abuse
9. **Regular backups** of configuration and data
10. **Test deployments** in staging before production

## Support

For deployment issues:
- Check logs: `docker logs` or `kubectl logs`
- Verify configuration: Environment variables set correctly?
- Test locally: Run `docker run -it --rm refactor-mcp:latest`
- Review documentation: See README.md and STATUS.md

For production support, consider FastMCP Cloud's managed deployment option.
