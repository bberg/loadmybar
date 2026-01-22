import urllib

import requests
from bs4 import BeautifulSoup
from flask import request, render_template, jsonify
from openai import OpenAI  # or your specific OpenAI client setup
from utils import perform_search, fetch_url, NOTION_API_KEY, NOTION_PARENT_PAGE_ID, notion, load_properties
from utils import client, get_database_entries, sanitize_notion_input, clean_html_content, is_valid_link, calculate_gpt_processing_cost, truncate_to_token_limit, fetch_google_results, get_key_data
from flask import render_template
from urllib.parse import urlparse
from pydantic import BaseModel
from typing import List
import json
import os

import markdown
TOPIC_DETALS_DATABASE = "171d4c22df478027927eebb7d2a6829e"

def register_tag_routes(app):
    @app.route('/generate_all_tags', methods=['POST'])
    def generate_all_tags():
        database_id = request.form.get("database_id")
        page_id = request.form.get("page_id")
        suggested_tags = generate_all_tags_func(database_id, page_id)
        return render_template('index.html', result=suggested_tags, key_data=get_key_data())

    @app.route('/assign_tags', methods=['POST'])
    def assign_tags():
        print("getting topics")
        database_id = request.form.get('database_id')  # Get the database ID from the query parameters
        relevance_threshold = request.form.get('relevance_threshold')
        assign_tags_func(database_id, relevance_threshold)
        return render_template('index.html', result="updated tags", key_data=get_key_data())


def generate_all_tags_func(database_id, page_id):
    print("generate_all_tags")
    total_cost = 0
    """Generate all tag suggestions for the database"""

    if not database_id:
        return "Database ID is required.", 400

    # Retrieve entries from the database
    entries = get_database_entries(database_id, False)
    print(f"Collecting data for {len(entries)} entries")

    all_content = ""

    # Concatenate all homepage content
    for entry in entries:
        homepage_content = entry['properties']['Homepage Content']['rich_text'][0]['plain_text']
        all_content += f'\n{homepage_content}'

    # Generate tags using GPT
    prompt = f"""
    Based on the following text, suggest catgories / prodcut offerings  etc. as "tags" that could be applied when searching through these different companies. Suggest a comma-separated list of 10-15 specific tags to distinguish between the companies in this directory. Make the tags smart, specific, meaningful and non-overlapping. Don't lead with any numbers or letters. capitalize. ALL ON ONE LINE, COMMA SEPARATED TAGS ONLY. \n\n\n ------ 
    {all_content}
    """
    print(len(prompt))
    prompt = truncate_to_token_limit(prompt, encoding_type="gpt-4o", max_tokens=127000)
    print(len(prompt))
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        suggested_tags = response.choices[0].message.content.strip()
        calculate_gpt_processing_cost(response)
        print(f"Suggested Tags: {suggested_tags}")
    except Exception as e:
        return f"Error generating tags: {e}", 500

    # Update the database with the generated tags
    try:
        notion.pages.update(
            parent={"database_id": database_id},
            page_id=page_id,
            properties={"all_tags": {"rich_text": [{"text": {"content": suggested_tags}}]}}
        )
    except Exception as e:
        return f"Error updating Notion database with tags: {e}", 500

    return suggested_tags


def assign_tags_func(database_id, relevance_threshold):

    if not database_id:
        return jsonify({"error": "No database ID provided"}), 400

    print('database queries started')
    entries = get_database_entries(database_id, include_omitted=False)
    topic_details = get_database_entries(TOPIC_DETALS_DATABASE)
    print('database queries complete')
    topic = None

    for entry in entries:
        print(f"assessing tags for:  {entry['properties']['Title']['title'][0]['text']['content']}")
        this_entry_tags = []
        for t in topic_details:
            if t['properties']['Original Page ID']['rich_text'][0]['plain_text'] == entry['id']:
                if t['properties']['Relevance']['number']:
                    if int(t['properties']['Relevance']['number']) > int(relevance_threshold):
                        if t['properties']['Topic']['rich_text']:
                            topic = t['properties']['Topic']['rich_text'][0]['plain_text'].replace("_", " ")
                            if topic not in this_entry_tags:
                                this_entry_tags.append({"name": topic})

        # Update the database with the generated tags
        try:
            notion.pages.update(
                parent={"database_id": database_id},
                page_id=entry['id'],
                properties={"tags": {"multi_select": this_entry_tags}}
            )
        except Exception as e:
            return f"Error updating Notion database with tags: {e}", 500