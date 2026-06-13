# AIOps Log Converter & Anomaly Detector

Automated log intelligence pipeline: **Gemini 1.5 Flash normalises raw unstructured logs into structured JSON**, then **Isolation Forest detects anomalies** — with Slack alerts and a GitHub Actions CI/CD workflow.

[![Python](https://skillicons.dev/icons?i=py,docker,githubactions)](https://skillicons.dev)

![Architecture](https://github.com/dev126712/aiops-log-converter/blob/7863a35a6b96ef1a9ff1e2437a70a6305b2f2eea/Untitled%20Diagram.drawio%20(3).png)

---

## Pipeline

```
raw_logs.txt  (unstructured text)
      │
      ▼
[Gemini 1.5 Flash]  — normalises to JSON Lines (JSONL)
      │
      ▼
[Isolation Forest]  — scores each log entry for anomaly probability
      │
      ├── normal → skip
      │
      ▼ anomaly
[Matplotlib]  — generates anomaly scatter plot report
      │
      ▼
[Slack Webhook]  — posts alert with anomaly summary
```

---

## Stack

| Component | Technology |
|---|---|
| **AI normalisation** | Google Gemini 1.5 Flash |
| **ML detection** | scikit-learn Isolation Forest |
| **Features** | Log severity score + message length |
| **Alerting** | Slack Incoming Webhook |
| **Visualisation** | Matplotlib |
| **Container** | Docker |
| **CI/CD** | GitHub Actions |

---

## Quick Start

```bash
git clone https://github.com/dev126712/aiops-log-converter
cd aiops-log-converter

# Configure
cp .env.example .env
# Fill in: GEMINI_API_KEY, SLACK_URL, LOG_FILE_NAME

# Run with Docker
docker build -t ai-log-analyzer .
docker run --rm \
    --env-file .env \
    -v $(pwd)/app.log:/app/app.log \
    -v $(pwd)/raw_logs.txt:/app/raw_logs.txt \
    ai-log-analyzer

# Or with Makefile
make analyze
```

### Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python aiops_log_converter.py
```

---

## Configuration

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `SLACK_URL` | Slack Incoming Webhook URL |
| `LOG_FILE_NAME` | Log file to analyse (default: `app.log`) |

---

> **See also:** [AIOps Log Converter 2.0](https://github.com/dev126712/aiops-log-converter2.0) — the production version with Loki, Redis, MongoDB, Prometheus, Grafana, and a provider-agnostic LLM router.
