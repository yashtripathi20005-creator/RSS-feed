import os
import feedparser
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import json
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# File to store user's feeds
FEEDS_FILE = 'feeds.json'

def load_feeds():
    """Load saved RSS feeds from JSON file"""
    if os.path.exists(FEEDS_FILE):
        with open(FEEDS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_feeds(feeds):
    """Save RSS feeds to JSON file"""
    with open(FEEDS_FILE, 'w') as f:
        json.dump(feeds, f, indent=2)

def parse_feed(url):
    """Parse an RSS feed and return the entries"""
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            return None, f"Error parsing feed: {feed.bozo_exception}"
        if not feed.entries:
            return None, "No entries found in this feed"
        return feed, None
    except Exception as e:
        return None, f"Error fetching feed: {str(e)}"

def extract_feed_info(feed):
    """Extract feed metadata"""
    return {
        'title': feed.feed.get('title', 'Untitled Feed'),
        'link': feed.feed.get('link', '#'),
        'description': feed.feed.get('description', ''),
        'entries': feed.entries
    }

def format_entry(entry):
    """Format a feed entry for display"""
    return {
        'title': entry.get('title', 'No title'),
        'link': entry.get('link', '#'),
        'published': entry.get('published', ''),
        'published_parsed': entry.get('published_parsed'),
        'summary': entry.get('summary', 'No summary available'),
        'description': entry.get('description', ''),
        'author': entry.get('author', 'Unknown author')
    }

def get_feed_entries_with_metadata(feed_url):
    """Get feed entries with additional metadata"""
    feed, error = parse_feed(feed_url)
    if error:
        return None, error
    
    feed_info = extract_feed_info(feed)
    formatted_entries = [format_entry(entry) for entry in feed_info['entries']]
    
    return {
        'title': feed_info['title'],
        'link': feed_info['link'],
        'description': feed_info['description'],
        'entries': formatted_entries,
        'total_entries': len(formatted_entries)
    }, None

def validate_url(url):
    """Validate if the URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@app.route('/')
def index():
    """Home page - show all saved feeds with their latest entries"""
    feeds = load_feeds()
    feed_data = []
    
    for feed in feeds:
        data, error = get_feed_entries_with_metadata(feed['url'])
        if data:
            # Get only the latest 5 entries
            data['entries'] = data['entries'][:5]
            feed_data.append({
                'url': feed['url'],
                'data': data,
                'error': None
            })
        else:
            feed_data.append({
                'url': feed['url'],
                'data': None,
                'error': error
            })
    
    return render_template('index.html', feeds=feed_data)

@app.route('/add', methods=['GET', 'POST'])
def add_feed():
    """Add a new RSS feed"""
    if request.method == 'POST':
        feed_url = request.form.get('feed_url', '').strip()
        
        if not feed_url:
            flash('Please enter a valid RSS feed URL', 'error')
            return redirect(url_for('add_feed'))
        
        if not validate_url(feed_url):
            flash('Invalid URL format. Please enter a valid URL (e.g., https://example.com/feed)', 'error')
            return redirect(url_for('add_feed'))
        
        # Check if feed already exists
        feeds = load_feeds()
        if any(f['url'] == feed_url for f in feeds):
            flash('This feed is already in your list', 'info')
            return redirect(url_for('index'))
        
        # Try to parse the feed to validate it
        feed, error = parse_feed(feed_url)
        if error:
            flash(f'Invalid RSS feed: {error}', 'error')
            return redirect(url_for('add_feed'))
        
        # Save the feed
        feeds.append({'url': feed_url})
        save_feeds(feeds)
        flash('RSS feed added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_feed.html')

@app.route('/remove/<path:feed_url>')
def remove_feed(feed_url):
    """Remove an RSS feed from the list"""
    feeds = load_feeds()
    feeds = [f for f in feeds if f['url'] != feed_url]
    save_feeds(feeds)
    flash('Feed removed successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/feed/<path:feed_url>')
def view_feed(feed_url):
    """View a single feed with all its entries"""
    feeds = load_feeds()
    if not any(f['url'] == feed_url for f in feeds):
        flash('Feed not found', 'error')
        return redirect(url_for('index'))
    
    data, error = get_feed_entries_with_metadata(feed_url)
    if error:
        flash(f'Error loading feed: {error}', 'error')
        return redirect(url_for('index'))
    
    return render_template('feed.html', feed=data, feed_url=feed_url)

@app.route('/refresh')
def refresh_feeds():
    """Refresh all feeds"""
    # This just reloads the page, the actual refresh happens on each request
    flash('Feeds refreshed successfully!', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', error='Internal server error'), 500

if __name__ == '__main__':
    # Create necessary directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Initialize feeds file if it doesn't exist
    if not os.path.exists(FEEDS_FILE):
        save_feeds([])
    
    app.run(debug=True, host='0.0.0.0', port=5000)
