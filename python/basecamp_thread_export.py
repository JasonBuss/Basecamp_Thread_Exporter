#!/usr/bin/env python3
"""Export a Basecamp Classic post and all its comments to readable UTF-8 text."""
import argparse
import html
import os
import re
import sys
import keyring
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit('Missing dependencies. Run: py -m pip install requests beautifulsoup4')


def text_of(node, tag):
    child = node.find(tag)
    return ''.join(child.itertext()).strip() if child is not None else ''


def body_of(node):
    child = node.find('body')
    if child is None or not ''.join(child.itertext()).strip():
        child = node.find('display-body')
    if child is None:
        return ''
    raw = ''.join(ET.tostring(child, encoding='unicode', method='html').split('>', 1)[1].rsplit('</', 1)[:1])
    soup = BeautifulSoup(html.unescape(raw), 'html.parser')
    for br in soup.find_all('br'):
        br.replace_with('\n')
    for tag in soup.find_all(['p', 'div', 'li', 'blockquote', 'tr']):
        tag.insert_before('\n')
        tag.insert_after('\n')
    for a in soup.find_all('a', href=True):
        label = a.get_text(' ', strip=True)
        href = a['href']
        a.replace_with(f'{label} ({href})' if label and label != href else href)
    value = soup.get_text(' ', strip=False)
    value = re.sub(r'[ \t]+', ' ', value)
    value = re.sub(r' *\n *', '\n', value)
    return re.sub(r'\n{3,}', '\n\n', value).strip()


def format_date(value):
    if not value:
        return 'Unknown date'
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M UTC')
    except ValueError:
        return value


def attachments(node):
    found = []
    for item in node.findall('./attachments/attachment'):
        name = text_of(item, 'name') or text_of(item, 'original-filename') or '(unnamed attachment)'
        found.append((name, text_of(item, 'download-url')))
    return found


def get_xml(session, url):
    response = session.get(url, timeout=40, headers={'Accept': 'application/xml'})
    response.raise_for_status()
    try:
        return ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise RuntimeError(f'Invalid XML from {url}: {exc}') from exc


def export(url, token, output=None):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.basecamphq.com'):
        raise ValueError('Expected an HTTPS Basecamp Classic URL ending in .basecamphq.com')
    match = re.search(r'/posts/(\d+)(?:\.xml)?(?:/|$)', parsed.path)
    if not match:
        raise ValueError('Could not find a post ID in the URL.')
    post_id = match.group(1)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    session = requests.Session()
    session.auth = (token, 'X')
    session.headers['User-Agent'] = 'BasecampClassicThreadExporter/1.0'
    post = get_xml(session, f'{origin}/posts/{post_id}.xml')
    comments_url = f'{origin}/posts/{post_id}/comments.xml'
    seen_urls, comments = set(), {}
    expected = None
    while comments_url:
        if comments_url in seen_urls:
            raise RuntimeError('Pagination loop detected.')
        seen_urls.add(comments_url)
        root = get_xml(session, comments_url)
        if expected is None:
            count = root.get('count')
            expected = int(count) if count and count.isdigit() else None
        for comment in root.findall('comment'):
            cid = text_of(comment, 'id')
            if cid:
                comments[cid] = comment
        next_path = root.get('continued-at')
        if next_path:
            next_url = urljoin(origin, next_path)
            if urlparse(next_url).netloc != parsed.netloc:
                raise RuntimeError('Unexpected pagination host.')
            comments_url = next_url
        else:
            comments_url = None
        print(f'Retrieved {len(comments)} comments' + (f' of {expected}' if expected is not None else '') + '...', file=sys.stderr)
    if expected is not None and len(comments) != expected:
        raise RuntimeError(f'Incomplete export: expected {expected} comments but retrieved {len(comments)}. No file written.')
    title = text_of(post, 'title') or f'Post {post_id}'
    lines = [title, f'URL: {url}', f'Comments: {len(comments)}', '=' * 72, '',
             'ORIGINAL POST', f"Author: {text_of(post, 'author-name') or 'Unknown'}",
             f"Posted: {format_date(text_of(post, 'posted-on'))}", '', body_of(post)]
    for name, link in attachments(post):
        lines += ['', f'Attachment: {name}']
        if link:
            lines.append(f'Link: {link}')
    lines += ['', '=' * 72, 'COMMENTS']
    ordered = sorted(comments.values(), key=lambda c: (text_of(c, 'created-at'), text_of(c, 'id')))
    for i, comment in enumerate(ordered, 1):
        lines += ['', '-' * 72, f'COMMENT {i} of {len(ordered)}',
                  f"Author: {text_of(comment, 'author-name') or 'Unknown'}",
                  f"Posted: {format_date(text_of(comment, 'created-at'))}"]
        emailed = text_of(comment, 'emailed-from')
        if emailed:
            lines.append(f'Posted via email: {emailed}')
        lines += ['', body_of(comment)]
        for name, link in attachments(comment):
            lines += ['', f'Attachment: {name}']
            if link:
                lines.append(f'Link: {link}')
    target = Path(output) if output else Path(f'basecamp_thread_{post_id}.txt')
    target.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    return target, len(comments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', help='Basecamp Classic post URL')
    parser.add_argument('-o', '--output', help='Output text filename')
    args = parser.parse_args()
    url = args.url or input('Basecamp thread URL: ').strip()
    token = keyring.get_password("BasecampClassic", "api_token")

    if not token:
        sys.exit(
            "Basecamp API token not found in Windows Credential Manager."
        )
    try:
        path, count = export(url, token, args.output)
        print(f'Exported {count} comments to {path.resolve()}')
    except (requests.RequestException, ValueError, RuntimeError, OSError) as exc:
        sys.exit(f'Export failed: {exc}')

if __name__ == '__main__':
    main()
