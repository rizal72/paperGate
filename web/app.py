import logging
import posix_ipc
import re
import os
import sys
from datetime import datetime
from flask import Flask, render_template, flash, redirect, request, Response, send_file, jsonify
import feedparser

from system import System

# Import settings from core/settings.py (which wraps local_settings.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
try:
    import settings
except ImportError:
    print("ERROR: settings.py not found in core/")
    print("Please copy core/local_settings.py.example to core/local_settings.py and configure it")
    sys.exit(1)

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY

# Disable caching for development
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def add_no_cache_headers(response):
    """Add no-cache headers to all responses"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
try:
    mq = posix_ipc.MessageQueue("/epdtext_ipc")
    mq.block = False
except posix_ipc.PermissionsError:
    logging.error("couldn't open message queue")
    exit(1)


# Get available screens from core/screens directory
def get_available_screens():
    """
    Read all available screen modules from ../core/screens/ directory.
    Returns a sorted list of screen names (without .py extension).
    """
    screens_dir = os.path.join(os.path.dirname(__file__), '..', 'core', 'screens')
    available_screens = []

    try:
        if os.path.isdir(screens_dir):
            for filename in os.listdir(screens_dir):
                # Only include .py files, exclude hidden files, __init__.py and private modules
                if (filename.endswith('.py') and
                    not filename.startswith('_') and
                    not filename.startswith('.')):
                    screen_name = filename[:-3]  # Remove .py extension
                    available_screens.append(screen_name)
    except (OSError, IOError) as e:
        logging.warning(f"Could not read screens directory: {e}")

    return sorted(available_screens)


# Get active screens from local_settings.py
def get_active_screens():
    """
    Read active screen list from ../local_settings.py (project root).
    Parses the SCREENS list from the settings file.
    Returns a list of currently active screen names.
    """
    settings_file = os.path.join(os.path.dirname(__file__), '..', 'local_settings.py')
    active_screens = []

    try:
        with open(settings_file, 'r') as f:
            content = f.read()

        # Find SCREENS = [...] in the file
        # Use regex to extract the list
        match = re.search(r'SCREENS\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            screens_text = match.group(1)
            # Extract quoted strings (screen names)
            screen_names = re.findall(r'[\'"]([^\'"]+)[\'"]', screens_text)
            active_screens = screen_names
    except (OSError, IOError) as e:
        logging.warning(f"Could not read local_settings.py: {e}")
    except Exception as e:
        logging.warning(f"Could not parse SCREENS from local_settings.py: {e}")

    return active_screens


# Input validation
def validate_screen_name(screen_name):
    """
    Validate screen name to prevent command injection.
    Only allow alphanumeric characters, underscores, hyphens, and dots.
    """
    if not screen_name:
        return None
    # Allow only safe characters: letters, numbers, underscore, hyphen, dot
    if not re.match(r'^[a-zA-Z0-9_.-]+$', screen_name):
        return None
    # Limit length
    if len(screen_name) > 100:
        return None
    return screen_name


@app.route('/')
def index():
    available_screens = get_available_screens()
    active_screens = get_active_screens()

    # Filter available screens to show only those not yet active
    inactive_screens = [screen for screen in available_screens if screen not in active_screens]

    return render_template('index.html', system=System,
                         available_screens=inactive_screens,
                         active_screens=active_screens)


@app.route('/next_screen')
def next_screen():
    mq.send("next", timeout=10)
    flash("Sent 'next' message to paperGate")
    return redirect('/')


@app.route('/previous_screen')
def previous_screen():
    mq.send("previous", timeout=10)
    flash("Sent 'previous' message to paperGate")
    return redirect('/')


@app.route('/button0')
def button0():
    mq.send("button0", timeout=10)
    flash("Sent 'KEY1' message to paperGate")
    return redirect('/')


@app.route('/button1')
def button1():
    mq.send("button1", timeout=10)
    flash("Sent 'KEY2' message to paperGate")
    return redirect('/')


@app.route('/button2')
def button2():
    mq.send("button2", timeout=10)
    flash("Sent 'KEY3' message to paperGate")
    return redirect('/')


@app.route('/button3')
def button3():
    mq.send("button3", timeout=10)
    flash("Sent 'KEY4' message to paperGate")
    return redirect('/')


@app.route('/reload')
def reload():
    mq.send("reload", timeout=10)
    flash("Sent 'reload' message to paperGate")
    return redirect('/')


@app.route('/screen')
def screen():
    screen_name = request.args.get('screen')
    screen_name = validate_screen_name(screen_name)
    if not screen_name:
        flash("Invalid screen name. Only alphanumeric, underscore, hyphen, and dot allowed.", "error")
        return redirect('/')
    mq.send("screen " + screen_name, timeout=10)
    flash("Sent 'screen' message to paperGate")
    return redirect('/')


@app.route('/add_screen')
def add_screen():
    screen_name = request.args.get('screen')
    screen_name = validate_screen_name(screen_name)
    if not screen_name:
        flash("Invalid screen name. Only alphanumeric, underscore, hyphen, and dot allowed.", "error")
        return redirect('/')

    # Send IPC message to daemon (session-only, not persistent)
    mq.send("add_screen " + screen_name, timeout=10)
    flash(f"Added '{screen_name}' screen (session only - resets on reboot)", "success")

    return redirect('/')


@app.route('/remove_screen')
def remove_screen():
    screen_name = request.args.get('screen')
    screen_name = validate_screen_name(screen_name)
    if not screen_name:
        flash("Invalid screen name. Only alphanumeric, underscore, hyphen, and dot allowed.", "error")
        return redirect('/')

    # Send IPC message to daemon (session-only, not persistent)
    mq.send("remove_screen " + screen_name, timeout=10)
    flash(f"Removed '{screen_name}' screen (restored on reboot)", "success")

    return redirect('/')


@app.route('/display_screenshot/<screen_name>')
def display_screenshot(screen_name):
    """Serve a screenshot for a specific screen with no-cache headers."""
    # Validate screen name (security)
    screen_name = validate_screen_name(screen_name)
    if not screen_name:
        return "Invalid screen name", 400

    screenshot_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'core',
        'display',
        f'{screen_name}.png'
    )

    if not os.path.exists(screenshot_path):
        return f"Screenshot for '{screen_name}' not available", 404

    # Return image with no-cache headers
    response = send_file(
        screenshot_path,
        mimetype='image/png',
        max_age=0
    )
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/current_screen_name')
def current_screen_name():
    """Return the name of the currently displayed screen."""
    current_screen_file = os.path.join(
        os.path.dirname(__file__),
        '..',
        'core',
        'display',
        'current_screen.txt'
    )

    try:
        with open(current_screen_file, 'r') as f:
            screen_name = f.read().strip()
        return jsonify({'screen': screen_name}), 200
    except FileNotFoundError:
        return jsonify({'error': 'Current screen not available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/feed')
def feed_index():
    """RSS feed reader page - integrated from epdtext-feed"""
    articles = []

    for feed_url in settings.FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # Get first 10 entries per feed
                # Extract time
                time_str = ""
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                    time_str = dt.strftime("%H:%M")

                # Extract summary (remove HTML tags)
                summary = ""
                if hasattr(entry, 'summary'):
                    summary = entry.summary
                    # Simple HTML tag removal
                    summary = re.sub('<[^<]+?>', '', summary)

                articles.append({
                    'title': entry.title,
                    'summary': summary,
                    'published': time_str,
                    'link': entry.link if hasattr(entry, 'link') else ''
                })
        except Exception as e:
            logging.error(f"Failed to fetch feed {feed_url}: {e}")

    # Sort by time (most recent first)
    articles.sort(key=lambda x: x.get('published', ''), reverse=True)

    return render_template('feed.html', articles=articles, last_update=datetime.now())


if __name__ == '__main__':
    app.run(host='0.0.0.0')
