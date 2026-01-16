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


def ai_pre_process(raw_file_path, target_file_path):
    """
    Sends raw text to an LLM to be formatted 
    for the specific parser in the script.
    """
    # 1. Read the messy raw logs
    with open(raw_file_path, 'r') as f:
        raw_content = f.read()

    # 2. Call the AI (Example using a hypothetical 'ai_client')
    # The prompt would ask for the JSON format required by log-analysis.py
    structured_logs = ai_client.generate(
        prompt=f"Convert these logs to JSON lines with 'time' (ms), 'level' (int), and 'msg': {raw_content}"
    )

    # 3. Save it so the existing load_and_parse_logs() can read it
    with open(target_file_path, 'w') as f:
        f.write(structured_logs)


def convert_logs_with_ai(input_file, output_file):


    client = genai.Client(api_key=GEMINI_KEY)
    try:
        with open(input_file, "r") as f:
            raw_content = f.read()

        print("🤖 AI is restructuring your logs... please wait.")

    # System prompt defines the rules for the AI
        prompt = f"""
        You are a log normalization assistant. Convert the following raw logs into a JSON Line format.
        Each line must be a valid JSON object with these keys: 
        - "time": Unix timestamp in milliseconds
        - "level": Numeric (10=TRACE, 20=DEBUG, 30=INFO, 40=WARN, 50=ERROR)
        - "msg": The log message text
    
        Raw Logs:
        {raw_content}
        """

        response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
        )

        structured_data = response.text.replace('```json', '').replace('```', '').strip()

    # Save the AI's output to the path the script expects (e.g., app.log)
        with open(output_file, "w") as f:
            f.write(structured_data)
    
        print(f"✅ AI Conversion Complete. Structured logs saved to {output_file}")
    except Exception as e:
        print(f"⚠️ AI Conversion Failed: {e}")

def load_and_parse_logs(LOG_FILE_PATH):
    data = []

    if not os.path.exists(LOG_FILE_PATH):
        print(f"❌ ERROR: File {LOG_FILE_PATH} not found.")
        return pd.DataFrame()

    with open(LOG_FILE_PATH, "r") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse each line as a JSON object
                log_entry = json.loads(line)
                
                # Extract fields: 'time', 'level', and 'msg' (or 'message')
                timestamp = log_entry.get("time")
                # Convert numeric level to string (e.g., 30 -> "INFO")
                level_num = log_entry.get("level", 30)
                level = LEVEL_MAPPING.get(level_num, "INFO")
                message = log_entry.get("msg") or log_entry.get("message", "")

                if timestamp and message:
                    data.append([timestamp, level, message])
            except json.JSONDecodeError:
                continue # Skip lines that aren't valid JSON

    df = pd.DataFrame(data, columns=["timestamp", "level", "message"])
    if df.empty:
        print("❌ ERROR: No logs found! Check if the file contains valid JSON.")
    return df

def preprocess_data(df):
    # Your JSON logs use Unix timestamps (milliseconds), so we update the unit
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms', errors='coerce')
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

def trigger_alert(anomaly_count):
    if anomaly_count > 0:
        msg = f"AIOps ALERT: {anomaly_count} anomalies detected in system logs!"
        print(f"\n🔔 SENDING NOTIFICATION: {msg}")

        os.system(f'notify-send "AIOps Alert" "{msg}"')

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
        print("❌ ERROR: LOG_FILE_NAME environment variable is not set.")
        return

    RAW_INPUT = "raw_logs.txt"
    if os.path.exists(RAW_INPUT):
        print("🤖 Raw logs detected. Starting AI normalization...")
        convert_logs_with_ai(RAW_INPUT, LOG_FILE_PATH)

    df_raw_loads= load_and_parse_logs(LOG_FILE_PATH)
    if df_raw_loads.empty:
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
        #trigger_alert(len(anomalies))
        send_slack_alert(len(anomalies), anomalies)

    #generate_report(df_final)

if __name__ == "__main__":
    main()
