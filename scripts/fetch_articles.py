"""
Fetch article content from URLs
Simple web scraping with BeautifulSoup
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import requests
from bs4 import BeautifulSoup
from utils import load_yaml, save_json, sanitize_filename, log

def fetch_article(url):
    """Fetch and extract article text from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text - prioritize article or main content
        article = soup.find('article')
        if not article:
            article = soup.find('main')
        if not article:
            article = soup.find('div', class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower()))
        if not article:
            article = soup.body

        text = article.get_text(separator='\n', strip=True) if article else ""

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        return text

    except Exception as e:
        log(f"Error fetching article {url}: {str(e)}", "ERROR")
        return None

def fetch_all_articles(event_name=None):
    """Fetch all articles from sources.yaml"""
    sources = load_yaml('sources.yaml')['sources']

    fetched = 0
    failed = 0
    results = {'success': [], 'failed': []}

    for source in sources:
        if source['type'] != 'article':
            continue

        # Filter by event if specified
        if event_name and source.get('event') != event_name:
            continue

        log(f"Fetching article: {source['name']} - {source['analyst']}")

        text = fetch_article(source['url'])

        if text:
            # Save to data/articles/
            filename = f"{sanitize_filename(source['event'])}_{sanitize_filename(source['name'])}.txt"
            filepath = os.path.join('data', 'articles', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            log(f"✅ Saved: {filepath}")
            fetched += 1
            results['success'].append(f"{source['name']} ({source['analyst']})")
        else:
            log(f"❌ Failed: {source['name']}", "ERROR")
            failed += 1
            results['failed'].append(f"{source['name']} ({source['analyst']})")

    log(f"Article fetch complete: {fetched} succeeded, {failed} failed")
    return fetched, failed, results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch articles')
    parser.add_argument('--event', help='Event name to filter by (optional)')
    args = parser.parse_args()

    fetch_all_articles(args.event)
