from openai import OpenAI
import os
from ddgs import DDGS
import requests
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def call_llm(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def search_web_duckduckgo(query):
    results = DDGS().text(query, max_results=5)

    results_str = "\n\n".join([
        f"Title: {r['title']}\n"
        f"URL: {r['href']}\n"
        f"Snippet: {r['body']}"
        for r in results
    ])

    return results_str


def search_web_brave(query):

    url = "https://api.search.brave.com/res/v1/web/search"

    api_key = os.environ.get("BRAVE_API_KEY", "your-brave-api-key")

    headers = {
        "accept": "application/json",
        "Accept-Encoding": "gzip",
        "x-subscription-token": api_key
    }

    params = {
        "q": query
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        results = data["web"]["results"]

        results_str = "\n\n".join([
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Description: {r['description']}"
            for r in results
        ])

        return results_str

    else:
        return f"Request failed with status code: {response.status_code}"


if __name__ == "__main__":

    print("## Testing call_llm")

    prompt = "In a few words, what is the meaning of life?"

    print(f"## Prompt: {prompt}")

    response = call_llm(prompt)

    print(f"## Response: {response}")


    print("\n## Testing search_web")

    query = "Who won the Nobel Prize in Physics 2024?"

    print(f"## Query: {query}")

    results = search_web_duckduckgo(query)

    print(f"## Results:\n{results}")