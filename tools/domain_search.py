import os
import requests
from notion_client import Client
from openai import OpenAI

# ---------------------------
# 1) GPT + Domain Suggestion
# ---------------------------

def generate_domain_suggestions(openai_api_key, topic, direction="for a website about", number=100):
    """
    Generates a list of {number} domain name suggestions for the given topic using GPT.
    """
    # openai.api_key = openai_api_key
    client = OpenAI(api_key=openai_api_key)  # Replace with your actual API key or environment variable setup

    prompt = (
        f"Generate {number} brandable domain name suggestions very likely to rank well and drive traffic {direction} '{topic}'. "
        "Each suggestion should be in a separate line without extra commentary."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    # Split GPT’s response into lines; attempt to filter out empty or descriptive lines
    suggestions_raw = response.choices[0].message.content.split("\n")
    # Clean up each line
    suggestions = [
        s.strip().lstrip("0123456789. ")
        for s in suggestions_raw
        if s.strip()
    ]
    return suggestions


# ---------------------------
# 2) Check Availability
# ---------------------------

def check_domain_availability(domain, rapidapi_key, rapidapi_host="domainr.p.rapidapi.com"):
    """
    Checks domain availability using Domainr's RapidAPI endpoint.
    Returns a dictionary with domain availability details.
    """
    url = "https://domainr.p.rapidapi.com/v2/status"
    querystring = {
        "mashape-key": "YOUR_MASHAPE_KEY",  # or 'X-RapidAPI-Key' param, depending on your subscription
        "domain": domain
    }
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": rapidapi_host
    }

    response = requests.get(url, headers=headers, params=querystring)

    # Safety check
    # if response.status_code != 75:
    #     return {"domain": domain, "status": "unknown_error", "info": response.text, "response_status_code": response.status_code}

    data = response.json()
    # Domainr returns an array with domain statuses, e.g.:
    # data["status"] -> [{'domain': 'example.com', 'status': ['inactive']}]
    if "status" in data and len(data["status"]) > 0:
        return {
            "domain": domain,
            "status_codes": data["status"][0].get("status", []),
            "response_status_code": response.status_code,
            'info': response.text
        }
    else:
        return {
            "domain": domain,
            "status_codes": ["unknown_error"],
            "response_status_code": response.status_code,
            'info': response.text
        }


# ---------------------------
# 3) Use GPT to Pick "Best"
# ---------------------------

def pick_best_domain(openai_api_key, available_domains, topic):
    """
    Uses GPT to pick the "best" available domain from a list, based on any criteria you define.
    Example prompt: brandability, memorability, closeness to topic, etc.
    """
    # If no domains are available, just return None
    if not available_domains:
        return None

    domain_list_str = "\n".join(f"- {d}" for d in available_domains)
    prompt = (
        f"Topic: {topic}\n"
        "We have the following available domain names:\n"
        f"{domain_list_str}\n\n"
        "Order the domains from best to worst for generating traffic. Put one domain per line, no additional content on each line."
    )
    client = OpenAI(api_key=openai_api_key)  # Replace with your actual API key or environment variable setup


    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )


    suggestions_raw = response.choices[0].message.content.split("\n")
    # Clean up each line
    suggestions = [
        s.strip().lstrip("0123456789. ")
        for s in suggestions_raw
        if s.strip()
    ]
    return suggestions

# ---------------------------
# 4) Notion Integration
# ---------------------------

def update_notion_with_domain(notion_api_key, parent_page_id, topic, content):
    title = "Domain Ideas - "+topic
    content_text = ""
    for i in content:
        content_text += i + "\n"
    """
    Simple example to add a new page or update an existing one in the Notion database
    with the selected domain. Adjust to your Notion schema as needed.
    """
    notion = Client(auth=notion_api_key)
    # Example: Create a new page with the selected domain
    # (Adjust to match your Notion property schema)

    # def create_child_page(notion, parent_page_id, title, content):
    """
    Creates a child page under the specified parent page in Notion.

    :param notion: Notion client instance
    :param parent_page_id: The ID of the parent page
    :param title: The title of the child page
    :param content: The rich text content for the child page
    :return: Response from the Notion API
    """
    try:
        response = notion.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [{"type": "text", "text": {"content": title}}]
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content_text[:1999]}}]
                    },
                }
            ],
        )
        return response
    except Exception as e:
        print(f"Error creating child page: {e}")
        return None



# ---------------------------
# Main Script
# ---------------------------

if __name__ == "__main__":
    # Replace with your own keys

    # 1) Generate 100 domain suggestions
    topic = "compliance management software directory - targeted at folks seeking compliance management software"
    # topic = "parking management directory for b2b - for parking lot managers to find parking management solutions and software. Give some like parkingmanager.com"
    # topic = "None"
    direction="only give variants of complianceXXXXX.com (e.g. with different values for XXXX like solutions or manager) with the topic of"
    # direction="only give variants of parkingXXXXX.com (e.g. with different values for XXXX like solutions or manager) with the topic of"
    suggestions = generate_domain_suggestions(OPENAI_API_KEY, topic, direction, number=50)
    print(f"GPT suggested {len(suggestions)} domains for '{topic}':")
    for s in suggestions:
        print(s)

    # 2) Check availability
    available_domains = []
    for domain in suggestions:
        try:
            availability = check_domain_availability(domain, RAPIDAPI_KEY)
            print(f"{domain}: {availability}")

            # Adjust logic for determining if "available" - Domainr uses statuses like "inactive", "undelegated", etc.
            # For a quick check, you might look for 'inactive' or 'undelegated' or 'available' in status codes.
            if availability['status_codes'] in ["inactive", "undelegated", "available", "undelegated inactive"]:
                available_domains.append(domain)
                print("found available domain ----------------------------------------")
        except Exception as e:
            print(f"Error: {e} {domain} {availability}")

    print("\nAVAILABLE DOMAINS:")
    for d in available_domains:
        print(d)

    # 3) Use GPT to pick the "best" domain
    best_domain = pick_best_domain(OPENAI_API_KEY, available_domains, topic)
    print(f"\nBest domains in order (by GPT criteria):")
    for i in best_domain:
        print(i)

    # 4) (Optional) Update Notion database
    if best_domain:
        notion_page = update_notion_with_domain(NOTION_API_KEY, NOTION_PARENT_PAGE_ID, topic, best_domain)
        print(f"Added child page to Notion")
    else:
        print("No available domains to update Notion with.")
