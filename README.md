# 3-Tier Python DevOps Application

A small task-management application designed for DevOps practice.

## Architecture

- Frontend: HTML/CSS/JavaScript served by Nginx
- Backend: Python Flask REST API
- Database: MySQL 8.4
- Local orchestration: Docker Compose
- Later deployment target: Kubernetes on kind
- CI/CD target: GitHub Actions + Docker Hub + Argo CD + Argo CD Image Updater

## Local run

```bash
docker compose up --build
```

Open http://localhost:8080

Backend health endpoint: http://localhost:5000/api/health
