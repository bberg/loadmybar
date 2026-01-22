from flask import Flask, render_template, request
from notion_client import Client
from serpapi import GoogleSearch
import re
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image
from io import BytesIO
import time
from pathlib import Path
import random
from openai import OpenAI
from git import Repo
from github import Github
import git
import os
import shutil
import fal_client
import json
import unicodedata

# Load from environment variables
SERP_API_KEY = os.environ.get("SERP_API_KEY", "")
api_key = os.environ.get("OPENAI_API_KEY", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "")

client = OpenAI(api_key=api_key)
notion = Client(auth=NOTION_API_KEY)

from bs4 import BeautifulSoup


import tiktoken

def get_key_data():
    entries = get_database_entries('16ad4c22df4780568b10de36f306dafb')
    key_data = {}
    for entry in entries:
        key_data[entry['properties']['Title']['title'][0]['plain_text']] = {
            'title': entry['properties']['Title']['title'][0]['plain_text'] if 'title' in entry['properties'][
                'Title'] and entry['properties']['Title']['title'] else None,
            'dbid': entry['properties']['listings_database_id']['rich_text'][0][
                'plain_text'] if 'listings_database_id' in entry['properties'] and
                                 entry['properties']['listings_database_id']['rich_text'] else None,
            'repo': entry['properties']['repo_name']['rich_text'][0]['plain_text'] if 'repo_name' in entry[
                'properties'] and entry['properties']['repo_name']['rich_text'] else None,
            'tags': entry['properties']['all_tags']['rich_text'][0]['plain_text'] if 'all_tags' in entry[
                'properties'] and entry['properties']['all_tags']['rich_text'] else None,
            'pageid': entry['id'] if 'id' in entry else None
        }
    return key_data

def encoding_getter(encoding_type: str):
    """
    Returns the appropriate encoding based on the given encoding type (either an encoding string or a model name).
    """
    if "k_base" in encoding_type:
        return tiktoken.get_encoding(encoding_type)
    else:
        return tiktoken.encoding_for_model(encoding_type)

def tokenizer(string: str, encoding_type: str) -> list:
    """
    Returns the tokens in a text string using the specified encoding.
    """
    encoding = encoding_getter(encoding_type)
    tokens = encoding.encode(string)
    return tokens

def token_counter(string: str, encoding_type: str) -> int:
    """
    Returns the number of tokens in a text string using the specified encoding.
    """
    num_tokens = len(tokenizer(string, encoding_type))
    return num_tokens

def truncate_to_token_limit(content: str, encoding_type: str, max_tokens: int) -> str:
    """
    Truncates the content to ensure it stays within the token limit.
    """
    encoding = encoding_getter(encoding_type)
    tokens = encoding.encode(content)
    if len(tokens) > max_tokens:
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
    return content

def calculate_gpt_processing_cost(result):
    """
    Calculate the cost of GPT processing based on the result object.

    Args:
        result: The ChatCompletion result object containing token usage.
        cost_per_1k_tokens (float): Cost per 1000 tokens for the specific model (default is $0.03).

    Returns:
        float: The total cost of processing.
    """
    # Extract the total tokens used
    input_tokens = result.usage.prompt_tokens
    output_tokens = result.usage.completion_tokens

    # Calculate the cost
    input_cost = (input_tokens) * (2.50 / 1000000)
    output_cost = output_tokens * (10.00/1000000)
    cost = input_cost + output_cost

    print(f"GPT Cost: {cost:.3f}")
    return round(cost, 4)  # Return the cost rounded to 4 decimal places




def is_valid_link(href):
    """Filters out telephone and email links."""
    if href.startswith('mailto:') or href.startswith('tel:'):
        return False
    return True
def clean_html_content(html_content):
    """
    Remove HTML tags and non-visible content from the crawled content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Get visible text
    visible_text = soup.get_text(separator="\n")

    # Remove excessive whitespace and empty lines
    cleaned_text = "\n".join(line.strip() for line in visible_text.splitlines() if line.strip())

    return cleaned_text

def load_properties(entry):
    v = {}
    for i in entry['properties']:
        try:
            for n in entry['properties'][i]['rich_text']:
                if v.get(i):
                    v[i] += n['plain_text']
                else:
                    v[i] = n['plain_text']
        except:
            try:
                v[i] = entry['properties'][i]['number']
            except:
                pass
    return v


def sanitize_notion_input(input_text):
    return ''.join(c for c in input_text if unicodedata.category(c) != 'Cs')[:1999]

def get_database_entries(database_id, include_omitted=True, filter=None):
    """
    Retrieve all entries from the specified Notion database.

    Args:
        database_id (str): The ID of the Notion database to query.
        include_omitted (bool): Whether to include entries marked as omitted.
        filter (dict, optional): A filter object to apply when querying the database.

    Returns:
        list: A list of database entries matching the criteria.
    """
    entries = []
    has_more = True
    next_cursor = None

    while has_more:
        request_body = {"filter": filter} if filter else {}
        if next_cursor:
            request_body["start_cursor"] = next_cursor

        # Make the query request
        response = notion.databases.query(database_id=database_id, **request_body)

        # Extend entries and handle pagination
        entries.extend(response.get("results", []))
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    # Filter omitted entries locally if include_omitted is False
    if not include_omitted:
        entries = [entry for entry in entries if not entry['properties']['Omit']['checkbox']]

    return entries

def fetch_url(url, retries=1, timeout=10):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 403:
                print(f"403 Forbidden. Retrying {attempt + 1}/{retries} {url}...")
                time.sleep(random.uniform(2, 5))
            else:
                response.raise_for_status()
                return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}. Retrying {attempt + 1}/{retries}... {url}")
            time.sleep(random.uniform(2, 5))
    raise Exception("Failed to fetch URL after multiple retries.")

def perform_search(query, target_results=15):
    """Perform a search using SerpAPI and return up to target_results results."""
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "start": 0,
        "location": "United States"
    }
    all_results = []

    while len(all_results) < target_results:
        search = GoogleSearch(params)
        print(params)
        results = search.get_dict()
        result_count = len(results.get("organic_results", []))
        organic_results = results.get("organic_results", [])

        if not organic_results:
            # No more results to fetch
            break

        for result in organic_results:
            result["position"] = result.get("position", 0) + params["start"]

        all_results.extend(organic_results)
        params["start"] += result_count
        print(f"found {result_count} results, all results total: {len(all_results)}")
        # Update the start parameter to fetch the next page of results

        # If the current page has fewer results than requested, stop paginating
        if len(organic_results) < 3:
            break

    # Return only up to the target number of results
    return all_results[:target_results]

def fetch_google_results(topic, num_pages=5):
    """
    Fetches Google search results for a given topic.
    """
    search_results = perform_search(topic, num_pages)
    search_content_blocks = []

    for result in search_results:
        url = result.get("link")
        try:
            response = fetch_url(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find('body').get_text(strip=True)
            search_content_blocks.append(content)
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    return search_content_blocks

def push_to_github(local_path, repo_url=None, comment="unspecified comment"):
    # Open the local repository
    repo = git.Repo(local_path)

    if repo_url:
        # Add remote origin
        if "origin" not in [remote.name for remote in repo.remotes]:
            repo.create_remote("origin", repo_url)
        else:
            repo.remotes.origin.set_url(repo_url)

    # Push to GitHub
    repo.git.add(A=True)  # Add all files
    repo.index.commit(comment)
    repo.remotes.origin.push(refspec="main:main")
    print(f"Local repository pushed to GitHub at {repo_url}.")
