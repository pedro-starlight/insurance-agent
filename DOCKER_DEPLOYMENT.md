# Docker Deployment Guide

This guide explains how to build and deploy the frontend and backend containers.

## Prerequisites

- Docker installed and running
- Docker Compose (optional, for local development)

## Project Structure

- `backend/Dockerfile` - Backend container (FastAPI)
- `frontend/Dockerfile` - Frontend container (Next.js)
- `docker-compose.yml` - Local development setup

## Building the Containers

### Backend Container

```bash
cd backend
docker build -t insurance-agent-backend:latest .
```

### Frontend Container

```bash
cd frontend
docker build -t insurance-agent-frontend:latest .
```

Or build with custom backend URL:

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=https://your-backend-url.com -t insurance-agent-frontend:latest .
```

## Running Locally with Docker Compose

1. Create a `.env` file in the root directory with your environment variables:

```env
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_AGENT_ID=your_agent_id_here
ELEVENLABS_WEBHOOK_SECRET=your_secret_here
OPENAI_API_KEY=your_key_here
```

2. Run with Docker Compose:

```bash
docker-compose up --build
```

This will start both containers:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Running Containers Individually

### Backend

```bash
docker run -d \
  --name insurance-agent-backend \
  -p 8000:8000 \
  -e ELEVENLABS_API_KEY=your_key \
  -e ELEVENLABS_AGENT_ID=your_agent_id \
  -e ELEVENLABS_WEBHOOK_SECRET=your_secret \
  -e OPENAI_API_KEY=your_key \
  insurance-agent-backend:latest
```

### Frontend

```bash
docker run -d \
  --name insurance-agent-frontend \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  insurance-agent-frontend:latest
```

## Deploying to Azure Container Apps

### Prerequisites

- Azure CLI installed and configured
- Docker images pushed to Azure Container Registry (ACR) or Docker Hub

### Step 1: Create Azure Container Registry (if not using Docker Hub)

```bash
# Create resource group
az group create --name insurance-agent-rg --location eastus

# Create container registry
az acr create --resource-group insurance-agent-rg --name insuranceagentacr --sku Basic

# Login to ACR
az acr login --name insuranceagentacr
```

### Step 2: Build and Push Images

```bash
# Tag and push backend
docker tag insurance-agent-backend:latest insuranceagentacr.azurecr.io/insurance-agent-backend:latest
docker push insuranceagentacr.azurecr.io/insurance-agent-backend:latest

# Tag and push frontend
docker tag insurance-agent-frontend:latest insuranceagentacr.azurecr.io/insurance-agent-frontend:latest
docker push insuranceagentacr.azurecr.io/insurance-agent-frontend:latest
```

### Step 3: Create Container Apps Environment

```bash
# Create Container Apps environment
az containerapp env create \
  --name insurance-agent-env \
  --resource-group insurance-agent-rg \
  --location eastus
```

### Step 4: Deploy Backend Container App

```bash
az containerapp create \
  --name insurance-agent-backend \
  --resource-group insurance-agent-rg \
  --environment insurance-agent-env \
  --image insuranceagentacr.azurecr.io/insurance-agent-backend:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    ELEVENLABS_API_KEY=your_key \
    ELEVENLABS_AGENT_ID=your_agent_id \
    ELEVENLABS_WEBHOOK_SECRET=your_secret \
    OPENAI_API_KEY=your_key \
  --registry-server insuranceagentacr.azurecr.io \
  --cpu 1.0 \
  --memory 2.0Gi
```

### Step 5: Deploy Frontend Container App

```bash
# Get backend URL (from previous step)
BACKEND_URL=$(az containerapp show --name insurance-agent-backend --resource-group insurance-agent-rg --query properties.configuration.ingress.fqdn -o tsv)

az containerapp create \
  --name insurance-agent-frontend \
  --resource-group insurance-agent-rg \
  --environment insurance-agent-env \
  --image insuranceagentacr.azurecr.io/insurance-agent-frontend:latest \
  --target-port 3000 \
  --ingress external \
  --env-vars \
    NEXT_PUBLIC_API_URL=https://${BACKEND_URL} \
  --registry-server insuranceagentacr.azurecr.io \
  --cpu 0.5 \
  --memory 1.0Gi
```

### Step 6: Get Application URLs

```bash
# Backend URL
az containerapp show --name insurance-agent-backend --resource-group insurance-agent-rg --query properties.configuration.ingress.fqdn -o tsv

# Frontend URL
az containerapp show --name insurance-agent-frontend --resource-group insurance-agent-rg --query properties.configuration.ingress.fqdn -o tsv
```

## Environment Variables

### Backend Required Variables

- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `ELEVENLABS_AGENT_ID` - ElevenLabs Conversational AI agent ID
- `ELEVENLABS_WEBHOOK_SECRET` - Webhook secret for signature verification
- `OPENAI_API_KEY` - OpenAI API key

### Frontend Required Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (must be set at build time for Next.js)

## Notes

- The frontend `NEXT_PUBLIC_API_URL` must be set at **build time** (not runtime) for Next.js to properly bundle it
- For Azure Container Apps, use the internal service name for backend communication if both apps are in the same environment
- Health checks are configured in both Dockerfiles
- Both containers run as non-root users for security

## Troubleshooting

### Backend Issues

- Check logs: `docker logs insurance-agent-backend`
- Verify environment variables are set correctly
- Ensure port 8000 is accessible

### Frontend Issues

- Check logs: `docker logs insurance-agent-frontend`
- Verify `NEXT_PUBLIC_API_URL` is set correctly at build time
- Check browser console for API connection errors
- Ensure backend is accessible from frontend container

### Azure Container Apps Issues

- Check container app logs in Azure Portal
- Verify container registry authentication
- Check ingress configuration
- Verify environment variables are set in Azure Portal

