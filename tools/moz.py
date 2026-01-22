import json
import requests
import os
from notion_client import Client
from serpapi import GoogleSearch

# Load from environment variables
MOZ_TOKEN = os.environ.get("MOZ_TOKEN", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")


def get_keyword_data(keyword):
    headers = {
        "x-moz-token": MOZ_TOKEN,
        "Content-Type": "application/json",
    }

    data = {
        "jsonrpc": "2.0",
        "id": "b8fe894a-89fe-4717-a50d-de2cba572f5f",
        "method": "data.keyword.search.intent.fetch",
        "params": {
            "data": {
                "serp_query": {
                    "keyword": keyword,
                    "locale": "en-US",
                    "device": "desktop",
                    "engine": "google"
                }
            }
        }
    }

    data = requests.post("https://api.moz.com/jsonrpc", headers=headers, data=json.dumps(data)).json()

    # Define the fixed keys
    fixed_keys = ["informational", "navigational", "commercial", "transactional"]

    # Create a dictionary with fixed keys and assign None as the default value
    intent_scores = {key: -1 for key in fixed_keys}

    # Update with actual scores if available
    try:
        for intent in data["result"]["keyword_intent"]["all_intents"]:
            if intent["label"] in intent_scores:
                intent_scores[intent["label"]] = intent["score"]
    except Exception as e:
        print(f"intent error {e}")


    headers = {
        "x-moz-token": MOZ_TOKEN,
        "Content-Type": "application/json",
    }

    data = {
        "jsonrpc": "2.0",
        "id": "b8fe894a-89fe-4717-a50d-de2cba572f5f",
        "method": "data.keyword.metrics.fetch",
        "params": {
            "data": {
                "serp_query": {
                    "keyword": keyword,
                    "locale": "en-US",
                    "device": "desktop",
                    "engine": "google"
                }
            }
        }
    }

    data = requests.post("https://api.moz.com/jsonrpc", headers=headers, data=json.dumps(data)).json()
    # Define the fixed keys
    fixed_keys = ["volume", "difficulty", "organic_ctr", "priority"]

    # Create a dictionary with fixed keys and assign None as the default value
    keyword_metrics = {key: -1 for key in fixed_keys}

    # Update with actual values if available
    try:
        metrics_data = data["result"].get("keyword_metrics", {})
        for key in fixed_keys:
            if key in metrics_data:
                keyword_metrics[key] = int(metrics_data[key])
    except Exception as e:
        print(f"metric error {e}")

    # Combine into a flat dictionary
    flattened_data = {
        **{f"intent_{key}": value for key, value in intent_scores.items()},
        **{f"{key}": value for key, value in keyword_metrics.items()}
    }
    print(flattened_data)
    return flattened_data

def update_notion_database():
    notion = Client(auth=NOTION_API_KEY)

    # Query the database
    query_results = notion.databases.query(database_id=NOTION_DATABASE_ID)

    for page in query_results["results"]:
        properties = page["properties"]
        title = properties['keyword']['title'][0]['plain_text'] if properties.get("keyword") else "Unknown"
        volume = properties.get("volume", {}).get("number")

        if volume is None:  # If "volume" field is missing, fetch and update keyword data
            print(f"Fetching data for keyword: {title}")
            keyword_data = get_keyword_data(title)

            # Update the page in Notion
            update_payload = {
                "properties": {
                    "volume": {"number": keyword_data.get("volume")},
                    "difficulty": {"number": keyword_data.get("difficulty")},
                    "organic_ctr": {"number": keyword_data.get("organic_ctr")},
                    "priority": {"number": keyword_data.get("priority")},
                    "intent_informational": {"number": keyword_data.get("intent_informational")},
                    "intent_navigational": {"number": keyword_data.get("intent_navigational")},
                    "intent_commercial": {"number": keyword_data.get("intent_commercial")},
                    "intent_transactional": {"number": keyword_data.get("intent_transactional")}
                }
            }

            notion.pages.update(page_id=page["id"], **update_payload)
            print(f"Updated keyword data for: {title}")

def add_keywords(keywords):
    notion = Client(auth=NOTION_API_KEY)

    for keyword in keywords:
        # Create a new page in the Notion database for each keyword
        try:
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "keyword": {
                        "title": [
                            {"text": {"content": keyword}}
                        ]
                    }
                }
            )
            print(f"Keyword '{keyword}' added to the database.")
        except Exception as e:
            print(f"Error adding keyword '{keyword}': {e}")



if __name__ == "__main__":

    update_notion_database()