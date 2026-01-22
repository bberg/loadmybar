import urllib
import random
import requests
from bs4 import BeautifulSoup
from flask import request, render_template, jsonify
from openai import OpenAI  # or your specific OpenAI client setup
from utils import perform_search, fetch_url, NOTION_API_KEY, NOTION_PARENT_PAGE_ID, notion, load_properties
from utils import client, get_database_entries, sanitize_notion_input, clean_html_content, is_valid_link, calculate_gpt_processing_cost, truncate_to_token_limit, fetch_google_results
from flask import render_template
from urllib.parse import urlparse
from pydantic import BaseModel
from typing import List
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import markdown
TOPIC_DETALS_DATABASE = "171d4c22df478027927eebb7d2a6829e"

def register_blog_routes(app):
    @app.route('/generate_blog', methods=['POST'])
    def generate_blog():
        topic = request.form.get("topic")
        num_pages = int(request.form.get("num_pages", 5))

        if not topic:
            return "Topic is required.", 400

        blog_post_md = crawl_and_generate_blog(topic, num_pages)

        # Convert Markdown to HTML
        blog_post_html = markdown.markdown(blog_post_md, extensions=['extra', 'codehilite', 'toc'])

        return render_template('blog_post.html', blog_post=blog_post_html)

    @app.route('/crawl_and_summarize', methods=['POST'])
    def crawl_and_summarize():
        """Crawl and summarize topics for a given set of database entries."""
        database_id = request.form.get("database_id")
        topics = request.form.get("tags")

        max_pages = int(request.form.get("max_pages", 5))  # Default to 5 pages

        if not database_id:
            return "Database ID is required.", 400


        crawl_and_summarize_func(database_id, topics, max_pages)
        # Retrieve entries from the database

        return f"Crawling and summarizing completed for topic '{topics}'"

    # @app.route('/generate_blog_with_notion', methods=['POST'])
    # def generate_blog_with_notion():
    #     database_id = request.form.get("database_id")
    #     topic = request.form.get("topic")
    #     num_pages = int(request.form.get("num_pages", 5))
    #
    #     if not database_id or not topic:
    #         return "Database ID and Topic are required.", 400
    #
    #     blog_post_md = read_notion_and_generate_blog(database_id, topic, num_pages)
    #
    #     # Convert Markdown to HTML
    #     blog_post_html = markdown.markdown(blog_post_md, extensions=['extra', 'codehilite', 'toc'])
    #
    #     return render_template('blog_post.html', blog_post=blog_post_html)

    @app.route('/read_notion_and_generate_blog_post_ideas', methods=['POST'])
    def read_notion_and_generate_blog_post_ideas():
        database_id = '171d4c22df478027927eebb7d2a6829e'
        topic = request.form.get("topics_list")
        general_topic = request.form.get("general_topic")
        repo_path = request.form.get("repo_path", None)
        num_pages = int(request.form.get("num_pages", 5))

        if not database_id or not topic:
            return "Database ID and Topic are required.", 400

        blog_post_md = read_notion_and_generate_blog_post_ideas_func(database_id, topic, num_pages, general_topic=general_topic, repoPath=repo_path)

        # Convert Markdown to HTML
        # blog_post_html = markdown.markdown(blog_post_md, extensions=['extra', 'codehilite', 'toc'])

        return "done!"

    @app.route('/get_topics', methods=['GET'])
    def get_topics():
        print("getting topics")
        database_id = request.args.get('database_id')  # Get the database ID from the query parameters

        if not database_id:
            return jsonify({"error": "No database ID provided"}), 400

        entries = get_database_entries(database_id)
        topic_details = get_database_entries(TOPIC_DETALS_DATABASE)

        page_id_list = []
        topic_list = []
        for entry in entries:
            page_id_list.append(entry["id"])

        for t in topic_details:
            # print(t)
            if t['properties']['Original Page ID']['rich_text'][0]['plain_text'] in page_id_list:
                if t['properties']['Topic']['rich_text']:
                    topic = t['properties']['Topic']['rich_text'][0]['plain_text']
                    if topic not in topic_list:
                        topic_list.append(topic)

        comma_separated_topics = ", ".join(topic.replace("_", " ") for topic in topic_list)

        return comma_separated_topics

# TODO confirm this is ok and remove this code...
# def crawl_and_summarize_func(database_id, topics, max_pages):
#     total_cost = 0
#     topic_list = topics.split(",")
#     entries = get_database_entries(database_id, False)
#     print(f"Collecting data for {len(entries)} entries")
#
#     # Iterate over each entry and perform the crawl
#     for entry in entries:
#         page_id = entry["id"]
#         url = entry["properties"].get("Link", {}).get("url")
#         if url:
#             this_cost = crawl_site_for_topics(page_id, topic_list, url, max_pages)
#             if this_cost:
#                 total_cost += this_cost
#             print(f"Total cost thus far: {total_cost}")

def crawl_and_summarize_func(database_id, topics, max_pages):
    total_cost = 0
    topic_list = topics.split(",")
    entries = get_database_entries(database_id, False)
    print(f"Collecting data for {len(entries)} entries")

    # Function to process a single entry
    def process_entry(entry):
        page_id = entry["id"]
        url = entry["properties"].get("Link", {}).get("url")
        if url:
            return crawl_site_for_topics(page_id, topic_list, url, max_pages)
        return 0

    # Use ThreadPoolExecutor for parallelization
    with ThreadPoolExecutor() as executor:
        # Submit tasks for each entry
        future_to_entry = {executor.submit(process_entry, entry): entry for entry in entries}

        # Collect results as they complete
        for future in as_completed(future_to_entry):
            try:
                result = future.result()
                total_cost += result
                print(f"Total cost thus far: {total_cost}")
            except Exception as e:
                print(f"Error processing entry: {e}")

    return total_cost

def crawl_and_generate_blog(topic, num_pages=5):
    """Crawls the web for a topic, collects data, and generates a blog post."""
    search_results = perform_search(topic, num_pages)
    content_blocks = []

    for result in search_results:
        url = result.get("link")
        try:
            response = fetch_url(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract main content (improve selectors for specific topics)
            content = soup.find('body').get_text(strip=True)
            content_blocks.append(content)
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Compile content into a prompt for GPT
    combined_content = "\n".join(content_blocks[:num_pages])
    prompt = f"""
    Write a detailed blog post on the topic "{topic}" based on the following content. Include an introduction, key points, and a conclusion. Output with .md file formatting:
    {combined_content[:8000]}  # GPT-4 token limit
    """

    # Generate blog post using GPT
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    blog_post = response.choices[0].message.content
    return blog_post


def create_crawl_results_database():
    """Create a new Notion database for storing crawl results."""
    properties = {
        "Title": {"title": {}},  # The title field will combine topic and site
        "Original Page ID": {"rich_text": {}},
        "Topic": {"rich_text": {}},
        "Site URL": {"url": {}},
        "Raw Data": {"rich_text": {}},
        "AI Summary": {"rich_text": {}}
    }

    database = notion.databases.create(
        parent={"type": "page_id", "page_id": NOTION_PARENT_PAGE_ID},
        title=[{"type": "text", "text": {"content": "Crawl Results"}}],
        properties=properties
    )
    return database["id"]


def check_topics_in_text(link_text: str, page_url: str, topics: List[str]) -> bool:
    for topic in topics:
        if topic.lower() in link_text.lower() or topic.lower() in page_url.lower():
            return True
    return False

def crawl_site_for_topics(page_id, topic_list, url, max_pages=5, results_db = '171d4c22df478027927eebb7d2a6829e'):
    """Crawl a website for pages relevant to a specific set of topics."""
    print(f"crawling {url} for topics {', '.join(topic_list)}")
    topic_list_sanitized = []
    object_of_topics = {}
    for i in topic_list:
        sanitized = i.strip().replace(" ","_")
        topic_list_sanitized.append(sanitized)
        object_of_topics[sanitized] = {
            "type": "string",
            "description": f"Summary of content provided about {i} specific to this company. if none available respond with 'none'(no quotes). This summary will be used directly on a directory webpage so don't mention 'the content' or the task'"
        }
        object_of_topics[sanitized+"_relevance"] = {
            "type": "integer",
            "description": f"Integer 0-10 relevance of {i} specific to this company based on the data provided. 0=no information, 10=this company is this or provides this service exactly"
        }
    required = list(object_of_topics.keys())

    summarize_topic_info = [
        {
            "type": "function",
            "function": {
                "name": "summarize_topic_info",
                "description": (
                    "Extract content highly related to the topics and record summaries about each topic in the response object"
                ),
                "parameters": {
                    "type": "object",
                    "properties": object_of_topics,
                    "required": required,
                    "additionalProperties": False,
                },
            }
        }
    ]
    # class Topic_Summaries(BaseModel):
    #     name: str
    #
    # for field_name in topic_list:
    #     setattr(Topic_Summaries, f"{field_name}_summary", (str, None))  # Adds the field as optional with a default of None
    #     # setattr(Topic_Summaries, f"{field_name}_present", (bool, False))  # Adds a boolean field for presence check

        # Dynamically add fields to the Topics class
    crawled_content = []
    try:
        response = fetch_url(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Collect topic-related links and non-topic links separately
        topic_related_links = []
        other_links = []
        scraped_links = []

        for link in soup.find_all('a', href=True):
            base_domain = urlparse(url).netloc
            href = link['href']
            if not is_valid_link(href):
                continue  # Skip telephone and email links
            # get the link url
            page_url = urllib.parse.urljoin(url, href)

            # Only process links on the same domain
            link_domain = urlparse(page_url).netloc
            if link_domain != base_domain:
                continue

            # prioritize pages with the topic in the link name or text
            if check_topics_in_text(link_domain, page_url, topic_list):
            # if topic.lower() in link.text.lower() or topic.lower() in page_url.lower():
                topic_related_links.append(page_url)
            else:
                other_links.append(page_url)

        # First, process topic-related links
        for page_url in topic_related_links:
            if len(crawled_content) >= max_pages:
                break
            try:
                page_resp = fetch_url(page_url)
                cleaned_text = clean_html_content(page_resp.text)  # Clean the HTML content
                crawled_content.append(cleaned_text)
                scraped_links.append(page_url)
            except Exception as e:
                print(f"Failed to fetch {page_url}: {e}")

        # Then, process other links if the limit hasn't been reached
        if len(crawled_content) < max_pages:
            for page_url in other_links:
                if len(crawled_content) >= max_pages:
                    break
                try:
                    page_resp = fetch_url(page_url)
                    cleaned_text = clean_html_content(page_resp.text)  # Clean the HTML content
                    crawled_content.append(cleaned_text)
                    scraped_links.append(page_url)
                except Exception as e:
                    print(f"Failed to fetch {page_url}: {e}")

        print("\n".join(scraped_links))

        # Combine and generate AI summary
        if len(crawled_content) > 0:
            combined_content = " ".join(crawled_content)
            topics_str = ', '.join(topic_list)
            prompt = f"Extract content highly related to the topics and record summaries about each topic in the response object TOPICS:'{topics_str}' \n 'Provide up to three paragraphs per topic. If none is available, return NONE only. Only summarize, do not provide information unrelated to the input content.\n CONTENT TO ANALYZE ---- \n {combined_content}"
            prompt = truncate_to_token_limit(prompt,encoding_type="gpt-4o", max_tokens=127000)
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                tools=summarize_topic_info,
                tool_choice= {"type": "function", "function": {"name": "summarize_topic_info"}}
            )

            cost = calculate_gpt_processing_cost(res)
            parsed = json.loads(res.choices[0].message.tool_calls[0].function.arguments)
            for i in topic_list_sanitized:
                ai_summary_text = parsed[i]
                relevance = int(parsed[i+"_relevance"])

                try:
                    notion.pages.create(
                        parent={"database_id": results_db},  # Replace with the ID of the crawl results database
                        properties={
                            "Title": {
                                "title": [{"type": "text", "text": {"content": f"{i} - {url}"}}]
                            },
                            "Original Page ID": {
                                "rich_text": [{"type": "text", "text": {"content": page_id}}]
                            },
                            "Topic": {
                                "rich_text": [{"type": "text", "text": {"content": i}}]
                            },
                            "Site URL": {"url": url},
                            "Raw Data": {
                                "rich_text": [{"type": "text", "text": {"content": sanitize_notion_input(combined_content)}}]
                            },
                            "AI Summary": {
                                "rich_text": [{"type": "text", "text": {"content": sanitize_notion_input(ai_summary_text)}}]
                            },
                            "Relevance": {"type": "number", "number": relevance}
                        }
                    )
                except Exception as e:
                    print(f"Error processing {url} for topic list'{', '.join(topic_list)}': {e}")

        return cost
    except Exception as e:
        print(f"Error processing {url} for topic '{i}': {e}")

def read_notion_and_generate_blog(database_id,topic,article_title,filename,reason,num_pages=3):
    """
    Reads AI summary data from the Notion database and pulls Google results
    as inputs to write a blog article.
    """
    # Fetch entries from the Notion database
    filter = {
        "and":[
            {
                "property":"Topic",
                "rich_text": {
                    "contains": topic
                }
            }
        ]
    }

    notion_entries = get_database_entries(database_id, filter=filter)

    if not notion_entries:
        print("No entries found in the database.")
        return "No entries found in the database.", 400

    # todo validate and remove
    # summary_dict = {}
    # for entry in notion_entries:
    #     if (entry['properties']['Topic']['rich_text'][0]['text']['content'] == topic):
    #         page = notion.pages.retrieve(entry['properties']['Original Page ID']['rich_text'][0]['text']['content'])
    #         title = page['properties']['Title']['title'][0]['text']['content']
    #         ai_summary = entry['properties']['AI Summary']['rich_text'][0]['text']['content']
    #         link = notion.pages.retrieve(entry['properties']['Original Page ID']['rich_text'][0]['text']['content'])['properties']['md_filename']['rich_text'][0]['text']['content']
    #         summary_dict[title] = {
    #             "summary": ai_summary,
    #             "link": f"/dir/{link.split('.')[0]}"
    #         }
    summary_dict = {}
    for entry in notion_entries:
        try:
            # Safely extract the topic property
            topic_property = entry.get('properties', {}).get('Topic', {}).get('rich_text', [])
            if topic_property and topic_property[0].get('text', {}).get('content') == topic:
                original_page_id_property = entry.get('properties', {}).get('Original Page ID', {}).get('rich_text', [])
                if original_page_id_property:
                    page_id = original_page_id_property[0].get('text', {}).get('content')
                    page = notion.pages.retrieve(page_id)

                    # Safely extract title
                    title_property = page.get('properties', {}).get('Title', {}).get('title', [])
                    title = title_property[0].get('text', {}).get('content',
                                                                  "Untitled") if title_property else "Untitled"

                    # Safely extract AI summary
                    ai_summary_property = entry.get('properties', {}).get('AI Summary', {}).get('rich_text', [])
                    ai_summary = ai_summary_property[0].get('text', {}).get('content',
                                                                            "No summary available") if ai_summary_property else "No summary available"

                    # Safely extract link
                    link_property = page.get('properties', {}).get('md_filename', {}).get('rich_text', [])
                    if not link_property or not link_property[0].get('text', {}).get('content'):
                        # Skip this entry if no valid link is found
                        continue

                    link = link_property[0].get('text', {}).get('content')
                    summary_dict[title] = {
                        "summary": ai_summary,
                        "link": f"/dir/{link.split('.')[0]}"
                    }
        except Exception as e:
            # Optionally log or handle the exception for debugging
            print(f"Error processing entry: {e}")


    # Fetch Google search results
    search_content_blocks = fetch_google_results(article_title, num_pages)

    # for i in
    # Combine AI summaries and search content

    combined_content = "LISTING DATA BY COMPANY"
    for i in summary_dict.keys():
        this_item = summary_dict[i]
        combined_content += f"\n-----\n {i} : link: {this_item['link'].lower()}\n{this_item['summary']}"

    combined_content += "\n\n\n".join(search_content_blocks[:num_pages])

    # Generate blog post with GPT
    prompt = f"""
    Write a blog article on "{topic}" with title {article_title} because {reason}
    Include a title, key considerations, a list of the top relevant companies. Output in Markdown format first row should be the title with # include markdown links to articles using the link directroy provided.
    First row after the title MUST be regular text (no heading).
    ONLY use relative links syntax [link text](/dir/pagename).
    DO NOT use the name of any companies in the title. 
    DO NOT use the word "listical" in the title.
    ------
    {combined_content}
    """

    prompt = truncate_to_token_limit(prompt,'gpt-4o',127000)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        calculate_gpt_processing_cost(response)
        blog_post = response.choices[0].message.content

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(blog_post)
                print(f"Blog post successfully written to {filename}")
        except Exception as e:
            print(f"Error saving blog post to file: {e}")

    except Exception as e:
        print(f"Error generating blog post: {e}")
        return "Error generating blog post.", 500

# todo confirm works and remove
# def read_notion_and_generate_blog_post_ideas_func(database_id, topic_list, num_pages=5, num_ideas=5, general_topic=None, repoPath=""):
#     """
#     Reads AI summary data from the Notion database and pulls Google results
#     as inputs to write a blog article.
#     """
#     try:
#         topic_list = topic_list.split(",")
#     except Exception as e:
#         print(f"Error processing {topic_list} for topic list, unable to comma separate assuming one entry only")
#         topic_list = [topic_list]
#     topic_list_sanitized = []
#     for i in topic_list:
#         sanitized = i.strip().replace(" ","_")
#         topic_list_sanitized.append(sanitized)
#
#     for topic in topic_list_sanitized:
#         # Fetch entries from the Notion database
#         notion_entries = get_database_entries(database_id)
#
#         if not notion_entries:
#             print("No entries found in the database.")
#             return "No entries found in the database.", 400
#
#         summary_dict = {}
#         for entry in notion_entries:
#             if (entry['properties']['Topic']['rich_text'][0]['text']['content'] == topic):
#                 page = notion.pages.retrieve(entry['properties']['Original Page ID']['rich_text'][0]['text']['content'])
#                 title = page['properties']['Title']['title'][0]['text']['content']
#                 ai_summary = entry['properties']['AI Summary']['rich_text'][0]['text']['content']
#                 summary_dict[title] = ai_summary
#
#         # Fetch Google search results
#         if general_topic:
#             search_topic = topic + " " + general_topic
#         else:
#             search_topic = topic
#         search_content_blocks = fetch_google_results(search_topic, num_pages)
#
#         # for i in
#         # Combine AI summaries and search content
#
#         combined_content = "LISTING DATA BY COMPANY"
#         for i in summary_dict.keys():
#             combined_content += f"\n-----\n {i}:\n{summary_dict[i]}"
#
#         combined_content += "\n".join(search_content_blocks[:num_pages])
#
#         # Generate blog post with GPT
#         prompt = f"""
#         provide {num_ideas}  blog post ideas (half of the ideas should be 'listical' style) for the content below, make it specific to the topic {topic}. All posts should be unique as they will exist on the same site.
#         Don't overly focus on one company.
#         {combined_content}  # GPT-4 token limit
#         """
#
#         prompt = truncate_to_token_limit(prompt,'gpt-4o',127000)
#
#         list_of_blog_post_ideas = [
#          {
#                 "type": "function",
#                 "function": {
#                     "name": "list_of_blog_post_ideas",
#                     "description": (
#                         "Provide a list of blog post ideas and the reasons for the post"
#                     ),
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "list_of_blog_post_ideas": {
#                                 "type": "array",
#                                 'minItems': num_ideas,
#                                 "items": {
#                                     "type": "object",
#                                     "properties": {
#                                         "title": {
#                                             "type": "string"
#                                         },
#                                         "title_filename": {
#                                             "type": "string",
#                                             "description": "a .md filename title for the blog post that is seo and url friendly"
#                                         },
#                                         "reason": {
#                                             "type": "string"
#                                         }
#                                     },
#                                     "required": [
#                                         "title",
#                                         "reason",
#                                         "title_filename"
#                                     ],
#                                     "additionalProperties": False
#                                 }
#                             }
#                         },
#                         "required": ["list_of_blog_post_ideas"],  # Fix: Make this an array
#                         "additionalProperties": False
#                     },
#                 }
#             }
#         ]
#
#         try:
#             res = client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[{"role": "user", "content": prompt}],
#                 tools=list_of_blog_post_ideas,
#                 tool_choice={"type": "function", "function": {"name": "list_of_blog_post_ideas"}}
#             )
#             calculate_gpt_processing_cost(res)
#             parsed = json.loads(res.choices[0].message.tool_calls[0].function.arguments)
#
#             # blog_post = res.choices[0].message.content
#             # return parsed
#             for a in parsed['list_of_blog_post_ideas']:
#                 filename = a['title_filename']
#                 filename = filename.replace(" ", "_")
#                 # Ensure the filename ends with .md
#                 if not filename.endswith(".md"):
#                     filename = filename.replace(".", "_")
#                     filename += ".md"
#                 filename = os.path.join(repoPath,'content','blog',filename)
#                 print(f"generating blog post {a['title']} with filename {filename}")
#                 try:
#                     read_notion_and_generate_blog(database_id,topic,article_title=a['title'],filename=filename,reason=a['reason'])
#                 except Exception as e:
#                     print(f"Error generating blog post {a['title']} with filename {filename} {e}")
#
#         except Exception as e:
#             print(f"Error generating blog post: {e}")
#             return "Error generating blog post.", 500


def process_topic(topic, database_id, num_pages, num_ideas, general_topic, repoPath, existing_articles=[]):
    """Processes a single topic to generate blog post ideas."""
    try:
        print(f"generating posts on {topic}")
        filter = {
            "and": [
                {
                    "property": "Topic",
                    "rich_text": {
                        "contains": topic
                    }
                }
            ]
        }

        notion_entries = get_database_entries(database_id, filter=filter)
        if not notion_entries:
            print(f"No entries found in the database for topic {topic}.")
            return
        else:
            print()

        summary_dict = {}
        for entry in notion_entries:
            if entry['properties']['Topic']['rich_text'][0]['text']['content'] == topic:
                page = notion.pages.retrieve(entry['properties']['Original Page ID']['rich_text'][0]['text']['content'])
                title = page['properties']['Title']['title'][0]['text']['content']
                ai_summary = entry['properties']['AI Summary']['rich_text'][0]['text']['content']
                summary_dict[title] = ai_summary

        search_topic = f"{topic} {general_topic}" if general_topic else topic
        search_content_blocks = fetch_google_results(search_topic, num_pages)

        combined_content = "LISTING DATA BY COMPANY"
        for title, summary in summary_dict.items():
            combined_content += f"\n-----\n {title}:\n{summary}"
        combined_content += "\n".join(search_content_blocks[:num_pages])

        listical_note = ""
        if num_ideas>1:
            listical_note = "(half of the ideas should be 'listical' style) "

        prompt = f"""
        Provide {num_ideas} blog post ideas {listical_note} for the content below, make it specific to the topic {topic}. All posts should be unique as they will exist on the same site.
        Don't overly focus on one company.
        """
        if len(existing_articles) > 0:
            prompt += f"\n Don't repeat these existing articles that are already published on the topic:"
            for article in existing_articles:
                prompt += f"\n - {article}"
        prompt += f"\n {combined_content}"

        prompt = truncate_to_token_limit(prompt, 'gpt-4o', 127000)

        list_of_blog_post_ideas = [
         {
                "type": "function",
                "function": {
                    "name": "list_of_blog_post_ideas",
                    "description": (
                        "Provide a list of blog post ideas and the reasons for the post"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "list_of_blog_post_ideas": {
                                "type": "array",
                                'minItems': num_ideas,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string"
                                        },
                                        "title_filename": {
                                            "type": "string",
                                            "description": "a .md filename title for the blog post that is seo and url friendly"
                                        },
                                        "reason": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "title",
                                        "reason",
                                        "title_filename"
                                    ],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["list_of_blog_post_ideas"],  # Fix: Make this an array
                        "additionalProperties": False
                    },
                }
            }
        ]

        res = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            tools=list_of_blog_post_ideas,
            tool_choice={"type": "function", "function": {"name": "list_of_blog_post_ideas"}}
        )
        calculate_gpt_processing_cost(res)
        parsed = json.loads(res.choices[0].message.tool_calls[0].function.arguments)
        print("Ideas found:")
        if parsed:
            try:
                for i in parsed['list_of_blog_post_ideas']:
                    print(i['title'])
            except Exception as e:
                print(f"Error processing {topic}: {e}")


        for idea in parsed['list_of_blog_post_ideas']:
            filename = idea['title_filename'].replace(" ", "_").replace(":", "_")
            title = idea['title'].replace(":", "")
            if not filename.endswith(".md"):
                filename = filename.replace(".", "_") + ".md"
            filepath = os.path.join(repoPath, 'content', 'blog', filename)
            print(f"Generating blog post {idea['title']} with filename {filepath}")
            try:
                read_notion_and_generate_blog(database_id, topic, article_title=title, filename=filepath, reason=idea['reason'])
            except Exception as e:
                print(f"Error generating blog post {idea['title']} with filename {filepath}: {e}")
    except Exception as e:
        print(f"Error processing topic {topic}: {e}")


def read_notion_and_generate_blog_post_ideas_func(database_id, topic_list, num_pages=5, num_ideas=5, general_topic=None, repoPath="", current_articles=[]):
    """
    Reads AI summary data from the Notion database and pulls Google results
    as inputs to write a blog article, parallelized for multiple topics.
    """
    print('generating blog posts')
    try:
        topic_list = topic_list.split(",")
    except Exception as e:
        print(f"Error processing {topic_list} for topic list, assuming a single entry.")
        topic_list = [topic_list]
    topic_list_sanitized = [t.strip().replace(" ", "_") for t in topic_list]

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(process_topic, topic, database_id, num_pages, num_ideas, general_topic, repoPath, current_articles): topic
            for topic in topic_list_sanitized
        }

        for future in as_completed(futures):
            topic = futures[future]
            try:
                future.result()  # Raise exceptions, if any
                print(f"Successfully processed topic: {topic}")
            except Exception as e:
                print(f"Error processing topic {topic}: {e}")

def post_new_article(database_id,topic_list,general_topic,repo_path,num_new=1):
    # get the names of all the existing files
    directory_path = os.path.join(repo_path,'content','blog')
    files_without_suffix = [
        os.path.splitext(file)[0] for file in os.listdir(directory_path) if
        os.path.isfile(os.path.join(directory_path, file))
    ]
    random_topic = random.choice(topic_list.split(","))
    read_notion_and_generate_blog_post_ideas_func(database_id,random_topic,5,num_new,general_topic,repo_path,files_without_suffix)