import urllib.request
import urllib.error
import json
import xml.etree.ElementTree as ET
import re
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']

SOURCES = [
    'https://feeds.feedburner.com/TheHackersNews',
    'https://www.bleepingcomputer.com/feed/',
    'https://krebsonsecurity.com/feed/',
]

print("Fetching RSS feeds...")
articles = []
for url in SOURCES:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        root = ET.fromstring(data)
        items = root.findall('.//item')
        print(f"  {url.split('/')[2]}: {len(items)} articles")
        for item in items[:10]:
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            desc = re.sub(r'<[^>]+>', '', item.findtext('description', '')).strip()[:250]
            articles.append({'title': title, 'link': link, 'desc': desc})
    except Exception as e:
        print(f"  ERROR {url}: {e}")

articles = articles[:10]
print(f"Total articles selected: {len(articles)}")

today = datetime.now().strftime('%A, %B %d, %Y')
articles_text = '\n\n'.join([
    f"{i+1}. {a['title']}\n   {a['desc']}\n   {a['link']}"
    for i, a in enumerate(articles)
])

prompt = (
    "You are a cybersecurity analyst. Below are today's top 10 cybersecurity news articles.\n\n"
    "Your task:\n"
    "1. Write a 3-sentence overall digest at the top highlighting the biggest threats and trends today.\n"
    "2. For each article, write ONE sentence summarizing it. On the next line, include the article URL exactly as provided, prefixed with \"\U0001f517 \".\n\n"
    "Format for Discord (plain text, no markdown headers). Keep the ENTIRE response under 1800 characters.\n\n"
    f"{articles_text}"
)

print("Calling Claude API...")
payload = json.dumps({
    "model": "claude-sonnet-4-6",
    "max_tokens": 800,
    "messages": [{"role": "user", "content": prompt}]
}).encode()

req = urllib.request.Request(
    'https://api.anthropic.com/v1/messages',
    data=payload,
    headers={
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
)

with urllib.request.urlopen(req, timeout=30) as r:
    result = json.loads(r.read())

digest = result['content'][0]['text']
print(f"Claude response: {len(digest)} chars")

header = f"**Cyber News Digest — {today}**\n" + "-" * 40 + "\n"
message = (header + digest)[:2000]

print("Posting to Discord...")
discord_payload = json.dumps({"content": message}).encode()
discord_req = urllib.request.Request(
    DISCORD_WEBHOOK_URL,
    data=discord_payload,
    headers={'content-type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(discord_req, timeout=15) as r:
        print(f"Discord response: {r.status}")
except urllib.error.HTTPError as e:
    print(f"Discord error {e.code}: {e.read().decode()}")
    sys.exit(1)

print("Done.")
