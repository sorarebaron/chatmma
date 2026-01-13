"""
Fetch YouTube video transcripts
Uses youtube-transcript-api
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from youtube_transcript_api import YouTubeTranscriptApi
from utils import load_yaml, load_config, sanitize_filename, log
import re

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\?/]+)',
        r'youtube\.com/embed/([^&\?/]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_transcript(url):
    """Fetch transcript for a YouTube video"""
    config = load_config()
    video_id = extract_video_id(url)

    if not video_id:
        log(f"Could not extract video ID from: {url}", "ERROR")
        return None

    try:
        # Try to get transcript
        languages = config['youtube']['transcript_languages']
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try manual transcript first
        try:
            transcript = transcript_list.find_manually_created_transcript(languages)
        except:
            # Fall back to auto-generated if configured
            if config['youtube']['fallback_to_auto_generated']:
                transcript = transcript_list.find_generated_transcript(languages)
            else:
                log(f"No manual transcript available for {video_id}", "ERROR")
                return None

        # Fetch the transcript
        transcript_data = transcript.fetch()

        # Combine into text
        full_text = ' '.join([item['text'] for item in transcript_data])

        # Check length limit
        max_length = config['youtube']['max_transcript_length']
        if len(full_text) > max_length:
            log(f"Transcript too long ({len(full_text)} chars), skipping", "WARNING")
            return None

        return full_text

    except Exception as e:
        log(f"Error fetching transcript for {video_id}: {str(e)}", "ERROR")
        return None

def fetch_all_transcripts(event_name=None):
    """Fetch all YouTube transcripts from sources.yaml"""
    sources = load_yaml('sources.yaml')['sources']

    fetched = 0
    failed = 0

    for source in sources:
        if source['type'] != 'youtube':
            continue

        # Filter by event if specified
        if event_name and source.get('event') != event_name:
            continue

        log(f"Fetching transcript: {source['name']} - {source['analyst']}")

        text = fetch_transcript(source['url'])

        if text:
            # Save to data/transcripts/
            filename = f"{sanitize_filename(source['event'])}_{sanitize_filename(source['name'])}.txt"
            filepath = os.path.join('data', 'transcripts', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            log(f"✅ Saved: {filepath}")
            fetched += 1
        else:
            log(f"❌ Failed: {source['name']}", "ERROR")
            failed += 1

    log(f"Transcript fetch complete: {fetched} succeeded, {failed} failed")
    return fetched, failed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts')
    parser.add_argument('--event', help='Event name to filter by (optional)')
    args = parser.parse_args()

    fetch_all_transcripts(args.event)
