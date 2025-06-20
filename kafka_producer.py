import pandas as pd
import json

# Load CSV
df = pd.read_csv('l1_day.csv')

# Convert ts_event to datetime and extract only time in HH:MM:SS format
df['ts_event'] = pd.to_datetime(df['ts_event']).dt.strftime('%H:%M:%S')

# Filter to correct time range
df = df[(df['ts_event'] >= '13:36:32') & (df['ts_event'] <= '13:45:14')]

# Sort and group by the new ts_event time string
df = df.sort_values(by='ts_event')
grouped = df.groupby('ts_event')

# Write to mock_stream.json
with open("mock_stream.json", "w", encoding="utf-8") as f:
    for timestamp, group in grouped:
        venues = []

        for _, row in group.iterrows():
            ask_price = row.get("ask_px_00")
            ask_size = row.get("ask_sz_00")

            # Filter out invalid rows
            if pd.isna(ask_price) or pd.isna(ask_size) or ask_size <= 0:
                continue

            venues.append({
                "venue": str(row["publisher_id"]),
                "ask": float(ask_price),
                "ask_size": float(ask_size),
                "fee": 0.01,
                "rebate": 0.002
            })

        if venues:
            message = {
                "timestamp": timestamp,
                "venues": venues
            }
            f.write(json.dumps(message) + "\n")
