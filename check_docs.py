import difflib
import glob
import os
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
import yaml
from mrkdwn_analysis import MarkdownAnalyzer

"""
PyYAML
requests
markdown-analysis
"""

###
# --- Configuration ---

# The path to glob for your documentation files.
CHARM_DIR = os.environ.get("INPUT_CHARM_DIR", ".")
DOCS_PATH_GLOB = os.environ.get("INPUT_DOCS_DIR", "docs")
# Environment variables for Discourse API access
# You may not need these if the posts are public,
# but it's required for private forums or rate-limiting.
DISCOURSE_URL = os.environ.get("INPUT_DISCOURSE_HOST", "https://discourse.charmhub.io")


# --- End Configuration ---

def parse_content_table(lines: list[str]) -> Dict[str, Any]:
    """
    Parse markdown table of contents and extract file paths.

    Args:
        content: The markdown content containing the TOC

    Returns:
        List of dictionaries containing parsed information
    """
    parsed_items = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Match markdown list items with links
        # Pattern: 1. [Title](path) or - [Title](path)
        match = re.match(r'^(\s*)(?:\d+\.\s*|\-\s*)\[([^\]]+)\]\(([^)]+\.md)\)', line)

        if match:
            indent, title, path = match.groups()
            level = len(indent) // 2 + 1  # Calculate nesting level

            parsed_items.append({
                'title': title,
                'path': path,
                'level': level,
                'indent': len(indent)
            })

    return parsed_items


def parse_file(filepath: str) -> Tuple[Optional[Dict[str, Any]], list[str]]:
    """
    Parses a Markdown file for YAML frontmatter and content.

    Returns:
        A tuple of (frontmatter_dict, content_str).
        If no frontmatter is found, frontmatter_dict will be None.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        return parse_content_table(lines), lines

    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None, ""


def fetch_discourse_content(post_url: str) -> str:
    """
    Fetches the raw Markdown content of a Discourse post.

    Handles URLs of the format:
    .../t/slug/12345 (topic ID, first post)
    .../t/slug/12345/2 (topic ID, post number 2)
    """

    # Extract base URL and path
    parsed_url = urlparse(post_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Check if the user-provided URL in the env var matches the post_url
    if DISCOURSE_URL and base_url != DISCOURSE_URL:
        print(f"Warning: URL in {post_url} does not match DISCOURSE_URL env var {DISCOURSE_URL}")
        # We'll use the base_url from the post itself

    if not DISCOURSE_URL and not base_url:
        raise ValueError("DISCOURSE_URL environment variable is not set and URL is relative.")

    # Regex to find topic ID and optional post number
    # /t/some-slug-here/12345
    # /t/some-slug-here/12345/2
    match = re.search(r'/t/[^/]+/(\d+)(?:/(\d+))?', parsed_url.path)

    if not match:
        raise ValueError(f"Could not parse topic ID or post number from URL: {post_url}")

    topic_id = match.group(1)
    post_number_str = match.group(2)

    # Default to post 1 (the topic itself) if no post number is specified
    post_number = int(post_number_str) if post_number_str else 1

    # Construct the API URL for the topic
    api_url = f"{base_url}/t/{topic_id}.json"

    headers = {
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = response.json()

        # Find the specific post in the stream
        post_list = data.get('post_stream', {}).get('posts', [])

        target_post = next((p for p in post_list if p['post_number'] == post_number), None)

        if not target_post:
            raise ValueError(f"Could not find post number {post_number} in topic {topic_id}")
        target_post = requests.get(f"{base_url}/posts/{target_post['id']}.json", headers=headers).json()
        return target_post.get('raw', '')

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching Discourse URL {api_url}: {e}")
    except (KeyError, ValueError) as e:
        raise Exception(f"Error parsing Discourse API response for {topic_id}: {e}")


def exclude_content_table(lines: list[str]) -> list[str]:
    """Exclude Contents section from the document."""
    result = []

    for line in lines:
        if line.strip() == '# Contents':
            break
        else:
            result.append(line)

    return result


def exclude_navigation_table(lines: list[str]) -> list[str]:
    """Exclude Navigation section from the document."""
    result = []

    for line in lines:
        if line.strip() == '# Navigation':
            break
        else:
            result.append(line)

    return result


class Navigation:
    name: str
    path: str
    topic: str

    def __init__(self, name: str, path: str, topic: str):
        self.name = name
        self.path = path
        self.topic = topic


def get_content_tree(table: list[dict]) -> dict:
    """
    Build a recursive content tree from a list of content items.
    Supports unlimited nesting levels.
    """

    def find_parent_node(stack: list, path: str):
        """Find the appropriate parent node for the given level."""
        # Remove items from stack that are at or deeper than target level
        if '/' not in path:
            return None
        parent_path = path.split('/')[0]
        while stack and stack[-1]['path'] != parent_path:
            stack.pop()
        return stack[-1] if stack else None

    tree = {}
    node_stack = []  # Stack to track parent nodes

    for item in table:
        link = extract_link(item['text'])
        path = link.get('url')
        title = link.get('text')

        current_node = {
            'path': path,
            'title': title,
            'children': []
        }

        if '/' not in path:
            # Top-level item - add directly to tree
            tree[title] = current_node
            node_stack = [current_node]
        else:
            # Find appropriate parent for this level
            parent = find_parent_node(node_stack, path)
            if parent:
                parent['children'].append(current_node)
                node_stack.append(current_node)
            else:
                # Fallback: treat as top-level if no appropriate parent found
                tree[title] = current_node
                node_stack = [current_node]

    return tree


def get_navigation_tree(table: list[list[str]]) -> dict:
    """
    Build a recursive navigation tree from a table of navigation items.
    Supports unlimited nesting levels.
    """

    def find_parent_node(stack: list, target_level: int):
        """Find the appropriate parent node for the given level."""
        # Remove items from stack that are at or deeper than target level
        while stack and stack[-1]['level'] >= target_level:
            stack.pop()
        return stack[-1] if stack else None

    tree = {}
    node_stack = []  # Stack to track parent nodes

    for row in table:
        level = int(row[0])
        path = row[1]
        navlink = row[2]
        link = extract_link(navlink)

        current_node = {
            'level': level,
            'path': path,
            'title': link.get('text'),
            'topic': link.get('url'),
            'children': []
        }

        if level == 1:
            # Top-level item - add directly to tree
            # Extract text from markdown link format [text](url)
            match = re.match(r'\[([^\]]+)\]', navlink)
            title = match.group(1) if match else navlink
            current_node['title'] = title
            tree[title] = current_node
            node_stack = [current_node]
        else:
            # Find appropriate parent for this level
            parent = find_parent_node(node_stack, level)
            if parent:
                parent['children'].append(current_node)
                node_stack.append(current_node)
            else:
                # Fallback: treat as top-level if no appropriate parent found
                tree[navlink] = current_node
                node_stack = [current_node]

    return tree


def extract_link(text: str) -> dict:
    analyzer = MarkdownAnalyzer.from_string(text)
    links = analyzer.identify_links().get('Text link')
    if links:
        return links[0]
    return {}


def convert_to_remote_path(local_path: str) -> str:
    """Convert local markdown path to remote Discourse path format."""
    # Example conversion logic; adjust as needed
    return local_path.replace('.md', '').replace('/', '-').lower()


def convert_to_local_path(parent_path: str, remote_path: str) -> str:
    """Convert remote Discourse path format to local markdown path."""
    # Example conversion logic; adjust as needed
    return remote_path.replace(f'{parent_path}-', f'{parent_path}/') + '.md'


def find_path_in_tree(remote: dict, remote_path: str) -> Optional[dict]:
    """Recursively search for a path in a navigation/content tree."""
    if remote.get('path') == remote_path:
        return remote
    for child in remote.get('children', []):
        result = find_path_in_tree(child, remote_path)
        if result:
            return result
    return None


def extract_navigation(remote_content: str, local_content: list[str]) -> list[Navigation]:
    remote_analyzer = MarkdownAnalyzer.from_string(remote_content)
    local_analyzer = MarkdownAnalyzer.from_string('\n'.join(local_content))
    content_table = local_analyzer.identify_lists().get("Ordered list", [])[0]
    tables = remote_analyzer.identify_tables().get('Table')
    navigation_table = []
    for table in tables:
        if ['Level', 'Path', 'Navlink'] == table.get('header'):
            navigation_table = table.get('rows')
            break

    navigation_tree = get_navigation_tree(navigation_table)
    content_tree = get_content_tree(content_table)
    local_to_remote = []
    for local in content_tree:
        remote = navigation_tree.get(local)
        if not remote:
            print(
                f"======ERROR=====\nContent and Navigation trees do not match! \nYou don't have {local.get('title', local)} in Discourse!\n================\n")
        for child in content_tree[local].get('children', []):
            remote_path = convert_to_remote_path(child.get('path'))
            child_remote = find_path_in_tree(remote, remote_path)
            if not child_remote:
                print(
                    f"======ERROR=====\nContent and Navigation trees do not match! \nYou don't have '{child.get('title', child)}' in Discourse!\n================\n")
                break
            local_to_remote.append(Navigation(child.get('title'), child.get('path'), child_remote.get('topic')))
        for remote_child in remote.get('children', []):
            local_path = convert_to_local_path(remote.get('path'), remote_child.get('path'))
            child_local = find_path_in_tree(content_tree[local], local_path)
            if not child_local:
                print(
                    f"======ERROR=====\nContent and Navigation trees do not match! \nYou don't have '{remote_child.get('title', remote_child)}' in GitHub!\nDiscourse link: {DISCOURSE_URL}/{remote_child.get('topic')}\n================\n")

    return local_to_remote


def generate_diff(local_content: list[str], remote_content: str, local_path: str, remote_url: str) -> str:
    """
    Generates a unified diff string between two content strings.
    Returns an empty string if no differences are found.
    """

    # Normalize content to avoid whitespace/line-ending issues
    local_lines = exclude_content_table([line.strip() for line in local_content])
    remote_lines = exclude_navigation_table([line.strip() for line in remote_content.splitlines()])

    diff = list(difflib.unified_diff(
        local_lines,
        remote_lines,
        fromfile=f"a/{local_path}",
        tofile=f"b/{remote_url}",
        lineterm=''
    ))

    navigation = extract_navigation(remote_content, local_content)

    for doc in navigation:
        parsed_url = urlparse(remote_url)
        topic_url = f"{parsed_url.scheme}://{parsed_url.hostname}{doc.topic}"
        remote_content = fetch_discourse_content(topic_url)
        _, local_content = parse_file(f"{DOCS_PATH_GLOB}/{doc.path}")
        local_lines = exclude_content_table([line.strip() for line in local_content])
        remote_lines = exclude_navigation_table([line.strip() for line in remote_content.splitlines()])

        diff += list(difflib.unified_diff(
            local_lines,
            remote_lines,
            fromfile=f"a/{DOCS_PATH_GLOB}/{doc.path}",
            tofile=f"b/{topic_url}",
            lineterm=''
        ))

    return "\n".join(diff)


def get_discourse_url(charm_dir: str) -> Optional[str]:
    """
    Extracts the 'discourse_url' from the charmcraft.yaml file.
    Returns None if not found.
    """
    try:
        if not os.path.exists(f"{charm_dir}/charmcraft.yaml"):
            raise FileNotFoundError(f"charmcraft.yaml not found in {charm_dir}")
        discourse_url = None
        with open(f"{charm_dir}/charmcraft.yaml", 'r', encoding='utf-8') as f:
            discourse_url = yaml.safe_load(f).get('links', {}).get('documentation')
        if not discourse_url:
            with open(f"{charm_dir}/metadata.yaml", 'r', encoding='utf-8') as f:
                discourse_url = yaml.safe_load(f).get('doc')
        return discourse_url
                
    except Exception as e:
        print(f"Error reading charmcraft.yaml {e.args}: {e}")
        return None


def main():
    """
    Main function to run the diff check.
    """
    print(f"Scanning for Markdown files in {DOCS_PATH_GLOB}...")

    files_to_check = glob.glob(f"{DOCS_PATH_GLOB}/index.md")
    if not files_to_check:
        print("No files found.")
        return

    diff_found = False

    for filepath in files_to_check:
        print(f"--- Checking {filepath} ---")
        frontmatter, local_content = parse_file(filepath)

        if not frontmatter:
            print(f"Skipping {filepath}: No valid frontmatter found.")
            continue

        discourse_url = get_discourse_url(CHARM_DIR)

        if not discourse_url:
            print(f"Skipping {filepath}: No 'discourse_url' key in frontmatter.")
            continue

        try:
            # 1. Fetch remote content
            print(f"Fetching: {discourse_url}")
            remote_content = fetch_discourse_content(discourse_url)

            # 2. Generate diff
            diff = generate_diff(local_content, remote_content, filepath, discourse_url)

            if diff:
                diff_found = True
                print(f"\n!!! DIFFERENCES FOUND for {filepath} !!!\n")
                print(diff)
                print("\n----------------------------------------\n")
            else:
                print(f"No differences found for {filepath}.")

        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            print("\n----------------------------------------\n")

    if diff_found:
        print("Diff check complete. Differences were found.")
        # In a CI environment, exit with an error code
        import sys
        sys.exit(1)
    else:
        print("Diff check complete. All checked files are in sync.")


if __name__ == "__main__":
    main()
