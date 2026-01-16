# AIOps Log Converter & Anomaly Detector
An automated pipeline that leverages Generative AI (Gemini 1.5 Flash) to normalize unstructured system logs and uses Machine Learning (Isolation Forest) to detect operational anomalies.

Project Overview:
- Ingestion: Raw, unstructured logs are placed in the project root as raw_logs.txt
- AI Normalization: The Python engine calls the Google Gemini API to restructure messy text into standardized JSON Lines (LTSV/JSONL).
- ML Analysis: The system loads the normalized logs into pandas and applies an Isolation Forest algorithm to identify statistical outliers based on log severity and message complexity.
- Alerting: Detected anomalies are visualized in a generated report and pushed to a Slack webhook for real-time SRE response.

Prerequisites
- Docker
- Google Gemini API Key
- Slack Webhook URL
- Makefile (Optional)

Make sure to change the log file name in .env and Makefile (In root directory)
````
GEMINI_API_KEY=your_api_key_here
SLACK_URL=your_slack_webhook_url_here
LOG_FILE_NAME=your-app.log
````
Makefile
````
LOG_NAME ?= your-app.log
````

Local Development (venv):
````
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
````

Deploy and Run (With make)
````
make analyze
````

Build (Docker):
````
docker build -t ai-log-analyzer .
````

Run (Docker):
````
docker run --rm \
    --env-file .env \
    -v $(pwd)/app.log:/app/app.log \
    -v $(pwd)/raw_logs.txt:/app/raw_logs.txt \
    ai-log-analyzer
````
Test
Runs test on 3 trype of log
![alt text](https://github.com/dev126712/aiops-log-converter/blob/0f467573b35fa422906cce0f4a58fc150532b582/image.png)

Author: Alexandre St-fort
