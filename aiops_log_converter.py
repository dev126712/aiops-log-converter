####################
#
# AI log converter & Anomaly Detector
# Description: Analyzes system logs to detect anomalies using Isolation Forest.
# Author: Alexandre St-fort
# Last modified: 01/15/26
#
####################

import os
import google.generativeai as genai
import json
import shutil
from google import genai
import io
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LOG_FILE_PATH = os.getenv("LOG_FILE_NAME")
SLACK_WEBHOOK_URL = os.getenv("SLACK_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
CONTAMINATION_RATE = "10%"
LEVEL_MAPPING = {
    10: 0,  # TRACE
    20: 0,  # DEBUG
    30: 1,  # INFO
    40: 2,  # WARN
    50: 3,  # ERROR
    60: 4   # FATAL
}

def percent_to_decimal(CONTAMINATION_RATE):
    CONTAMINATION_RATE = float(CONTAMINATION_RATE.strip('%'))
    print(CONTAMINATION_RATE)
    return CONTAMINATION_RATE / 100


def convert_logs_with_ai(input_file):


    client = genai.Client(api_key=GEMINI_KEY)
    try:
        with open(input_file, "r") as f:
            raw_content = f.read()

        if not raw_content.strip():
            print("⚠️ Input file is empty. Skipping AI conversion.")
            return pd.DataFrame()

        print("🤖 AI is restructuring your logs... please wait.")

    # System prompt defines the rules for the AI
        SYSTEM_INSTRUCTION = """
        
        You are an expert DevOps SRE "log normalization expert". Convert raw logs into a standardized JSON format.
        Strictly adhere to the following schema:

        {
            "timestamp": "ISO8601 string",
            "level": "Integer (10:TRACE, 30:INFO, 40:WARN, 50:ERROR)",
            "message": "Cleaned log message",
            "source": "Component name"
        }
        """

        FEW_SHOT_EXAMPLES = """
        Input: 2026-01-18 09:22:31 [WEB] INFO: User login success
        Output: {"timestamp": "2026-01-18T09:22:31Z", "level": 30, "message": "User login success", "source": "WEB"}

        Input: {"meta": {"sys": "DB"}, "text": "CRITICAL: Connection timeout", "t": 1737192151}
        Output: {"timestamp": "2026-01-18T09:22:31Z", "level": 50, "message": "Connection timeout", "source": "DB"}
        Input: [2026-01-18T09:22:31Z] WARN - Cache miss for key user_123
        Output: {"timestamp": "2026-01-18T09:22:31Z", "level": 40, "message": "Cache miss for key user_123",

        Raw Logs:
        {raw_content}
        """

        response_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "level": {"type": "integer"},
                    "message": {"type": "string"},
                    "source": {"type": "string"}
                },
                "required": ["timestamp", "level", "message", "source"]
            }
        }

        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=f"Convert these logs: {raw_content}",
            config={
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "system_instruction": "You are a log normalization expert. Convert logs to structured JSON.",
                "temperature": 0  
            }
        )

        structured_data = response.text
        
        # Clean up any markdown code blocks if the AI ignored the prompt instructions
        structured_data = structured_data.replace('```json', '').replace('```', '').strip()
        
        print(f"✅ AI Conversion Complete.")
        return load_and_parse_logs(structured_data, is_raw_string=True)
    except Exception as e:
        print(f"⚠️ AI Conversion Failed: {e}")
        return pd.DataFrame()


def load_and_parse_logs(input_source, is_raw_string=False):
    data = []
    try:
        # 1. Load the data
        if is_raw_string:
            # AI returns a single string containing a full JSON list
            data_list = json.loads(input_source)
        else:
            with open(input_source, "r") as f:
                data_list = json.load(f)

        # 2. Convert directly to DataFrame
        # Ensure the keys in the AI JSON match these column names
        df = pd.DataFrame(data_list)

        if df.empty:
            print("❌ ERROR: No logs found in the JSON structure.")
            return pd.DataFrame()

        # 3. Clean up column names to match the rest of your script
        # If the AI uses 'timestamp', rename it to 'time' or vice versa
        if "timestamp" in df.columns:
            df = df.rename(columns={"timestamp": "time"})
        if "message" in df.columns:
            df = df.rename(columns={"message": "msg"})

        print(f"✅ Successfully parsed {len(df)} logs.")
        return df

    except Exception as e:
        print(f"❌ JSON Parsing Error: {e}")
        return pd.DataFrame()


def preprocess_data(df):
    print(f"DEBUG: Current columns are: {df.columns.tolist()}")
    # Your JSON logs use Unix timestamps (milliseconds), so we update the unit
    df["timestamp"] = pd.to_datetime(df["time"], errors='coerce')
    df_clean = df.dropna(subset=["timestamp"]).copy()
    df_clean["level_score"] = df_clean["level"].replace(LEVEL_MAPPING).fillna(1)
    df_clean["message_length"] = df_clean["message"].apply(len)
    return df_clean

def detect_anomalies(df, CONTAMINATION_RATE):
    model = IsolationForest(contamination=CONTAMINATION_RATE, random_state=42)
    df["anomaly_code"] = model.fit_predict(df[["level_score", "message_length"]])
    df["status"] = df["anomaly_code"].apply(lambda x: "❌ ANOMALY" if x == -1 else "✅ NORMAL")
    print(f"\n✅ Analysis Complete! Processed {len(df)} log lines.")
    anomalies = df[df["status"] == "❌ ANOMALY"]
    if not anomalies.empty:
        print(anomalies[["timestamp", "level", "message", "status"]])
    else:
        print("No anomalies detected.")
    return df

def generate_report(df):
    colors = df['anomaly_code'].map({1: 'tab:green', -1: 'tab:red'})
    plt.figure(figsize=(10, 6))
    plt.scatter(df['level_score'], df['message_length'], c=colors, alpha=0.6)
    plt.title('AIOps Log Anomaly Detection')
    plt.xlabel('Log Severity (1=INFO, 4=CRITICAL)')
    plt.ylabel('Message Length (Characters)')
    plt.grid(True)
    plt.savefig('anomaly_report.png')
    print("\n📈 Graph saved successfully as 'anomaly_report.png'")

def send_slack_alert(anomaly_count, anomalies_df):
    if not SLACK_WEBHOOK_URL:
        print("ℹ️ SLACK_URL not set. Skipping Slack notification.")
        return

    if anomaly_count == 0:
        return

    summary = anomalies_df[['timestamp', 'level', 'message']].head(5).to_string(index=False)

    payload = {
        "text": "🚨 *AIOps Anomaly Detection Alert* 🚨",
        "attachments": [
            {
                "color": "#ff0000",
                "fields": [
                    {"title": "Total Anomalies Found", "value": str(anomaly_count), "short": True},
                    {"title": "Status", "value": "Action Required", "short": True},
                    {"title": "Top Anomalies Detected", "value": f"```{summary}```", "short": False}
                ],
                "footer": "Sent from AI-Log-Analyzer Engine"
            }
        ]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload))
        if response.status_code == 200:
            print("✅ Slack notification sent!")
        else:
            print(f"❌ Failed to send Slack alert: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error connecting to Slack: {e}")


def main():

    if not LOG_FILE_PATH:
        print("❌ ERROR: Make sure to set LOG_FILE_NAME variable in .env file.")
        return

    if os.path.exists(LOG_FILE_PATH):
        print("🤖 Raw logs detected. Starting AI normalization...")

        df_raw_loads = convert_logs_with_ai(LOG_FILE_PATH)

        if df_raw_loads is None or df_raw_loads.empty:
            print("No data to process...")
            return

        df_clean = preprocess_data(df_raw_loads)
        if df_clean.empty:
            print("ERROR: No valid timestamps found. Check log format.")
            return

        contamination = percent_to_decimal(CONTAMINATION_RATE)
        df_final = detect_anomalies(df_clean, contamination)
        anomalies = df_final[df_final["anomaly_code"] == -1]
        if not anomalies.empty:
            send_slack_alert(len(anomalies), anomalies)

        #generate_report(df_final)
    else:
        print(f"❌ ERROR: Log file {LOG_FILE_PATH} does not exist.")
        return  

if __name__ == "__main__":
    main()
