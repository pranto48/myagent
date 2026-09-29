# MyAgent (ampagent) - Enterprise AI Agent & Analytics Suite

[![Docker Image Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](https://hub.docker.com/r/itsupportbd/ampagent)
[![Docker Pulls](https://img.shields.io/docker/pulls/itsupportbd/ampagent.svg)](https://hub.docker.com/r/itsupportbd/ampagent)
[![License: IT Support BD](https://img.shields.io/badge/License-Proprietary-cyan.svg)](https://itsupport.com.bd)

**MyAgent (ampagent)** is a self-hosted, enterprise-grade Autonomous AI Agent and Operational Intelligence Suite built by **[IT support BD](https://itsupport.com.bd)** and architected by **[Arif Mahmud](https://arifmahmud.com/)**.

Equipped with a native **Autonomous Agent Operational Engine**, MyAgent features an interactive **Sessions Hub**, an in-browser virtual `/opt/data` **Filesystem Explorer**, an extensive **60-Skill Agent Library (36 Toolsets)** across 10 functional domains, bilingual Bengali/English real-time i18n support, and a dual-memory ChromaDB vector and SQLite FTS5 RAG engine.

---

## 🌟 Core Architectural Features

* **Autonomous Agent Operational Suite:**
  * **Sessions Hub:** Real-time KPI metrics (`Total`, `Active in store`, `Archived`, `Messages`, `Sources`), platform connection monitors (`api_server`, `webchat`, `cli`), and terminal TUI one-click jump.
  * **Filesystem Explorer (`/opt/data`):** Full in-browser directory explorer with drag-and-drop file ingestion, virtual path traversal protection, and breadcrumb navigation.
  * **60 Agent Skills Library:** 36 executable CLI/API toolsets and 24 procedural capabilities across 10 distinct categories with live search, square tile toggle, and autonomous learning (`Learn a skill`).
* **Enterprise Memory Architecture:**
  * Persistent SQLite WAL session stores and message vector indexing with ChromaDB.
  * SQLite FTS5 instant hybrid retrieval with table-aware chunking for Excel, PDF, and OCR images.
* **Dual-Language Internationalization (i18n):**
  * Seamless one-click switching between **Bangla (বাংলা)** and **English (EN)** with 811 synchronized keys.
* **Autonomous Cron & Telemetry:**
  * Automated background report generation, vector vacuums, security audit monitors, and live log stream console.

---

## 🏷️ Docker Image Tags

| Tag | Target Architecture | Description |
| :--- | :--- | :--- |
| `latest` | `linux/amd64` | Latest stable production release of MyAgent Suite |
| `v3.1.0` | `linux/amd64` | Production release featuring Autonomous Agent Sessions, Files, and 60-Skill Hub |
| `backend-latest` | `linux/amd64` | Standalone FastAPI AI & Memory Engine container |
| `frontend-latest` | `linux/amd64` | Standalone Nginx Web UI container |

---

## 🚀 Quick Start with Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  backend:
    image: itsupportbd/ampagent:v3.1.0-backend
    container_name: myagent-backend
    restart: unless-stopped
    ports:
      - "8008:8000"
    environment:
      - WEB_PORT=3399
      - BACKEND_PORT=8008
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=YourSecurePassword
      - JWT_SECRET=your-secret-token-key-2026
      - LLM_BASE_URL=http://192.168.20.10:11434/v1
      - LLM_API_KEY=not-needed
      - LLM_MODEL=llama3.3
      - AGENT_NAME=Company Data Intelligence Agent
      - DATA_DIR=/app/data
    volumes:
      - ./data:/app/data

  frontend:
    image: itsupportbd/ampagent:v3.1.0-web
    container_name: myagent-web
    restart: unless-stopped
    ports:
      - "3399:80"
    depends_on:
      - backend

networks:
  default:
    name: myagent-network
```

Run the stack:

```bash
docker compose up -d
```

Access the Web Portal at `http://<your-server-ip>:3399` with default credentials:
* **Username:** `admin`
* **Password:** `Aa987654`

---

## 🔒 Enterprise Security & Compliance

* **Data Loss Prevention (DLP):** Real-time regex masking of Credit Cards, Phone numbers, and API tokens.
* **Adaptive Firewall & Rate Limiting:** In-memory sliding window preventing brute-force authentication.
* **Cryptographic Vault:** AES-256-GCM encryption for stored secrets and paired client handshakes.

---

## 🏢 Credits & Support

* **Organization:** [IT support BD](https://itsupport.com.bd)
* **Lead Architect:** [Arif Mahmud](https://arifmahmud.com/)
* **Support Email:** `support@itsupport.com.bd`
* **Copyright:** © 2026 IT support BD. All rights reserved.
