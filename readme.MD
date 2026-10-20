# Basecamp Classic Thread Exporter

A Python utility for exporting complete discussion threads from Basecamp Classic into readable text files.

The utility retrieves the original post and all associated comments, automatically handling API pagination. The resulting text file is formatted for easy reading, sharing, or pasting into ChatGPT for analysis and discussion.

## Features

- Retrieves the original post, including title, author, date, and body.
- Retrieves all comments, automatically following Basecamp Classic's paginated API responses.
- Orders comments chronologically.
- Converts HTML content into readable plain text.
- Includes author names and posting dates.
- Identifies comments submitted via email.
- Lists attachments, including filenames and download URLs, without downloading the files.
- Validates the retrieved comment count to help identify incomplete exports.
- Saves the exported thread as a UTF-8 text file in the current working directory.
- Uses Windows Credential Manager to securely store the Basecamp API token.

## Requirements

- Windows
- Python 3
- Access to a Basecamp Classic account with API permissions

Python dependencies:

```text
requests
beautifulsoup4
keyring
```

Install dependencies using:

```bash
py -m pip install -r requirements.txt
```

## Authentication

Basecamp Classic uses an API authentication token.

### Obtaining the API Token

1. Log into Basecamp Classic.
2. Navigate to **My Info**.
3. Select **Show your tokens** under Authentication tokens.
4. Copy your API token.

### Storing the Token

The utility retrieves its API token from Windows Credential Manager using Python's `keyring` library.

The token should be stored using:

- **Service:** `BasecampClassic`
- **Username:** `api_token`

To store the token, start Python:

```bash
py
```

Then execute:

```python
import keyring
import getpass

token = getpass.getpass("Basecamp API token: ")
keyring.set_password("BasecampClassic", "api_token", token)
```

Exit Python:

```python
exit()
```

The token is now stored in Windows Credential Manager and will be retrieved automatically when running the utility.

**Security:** Never commit API tokens or other credentials to the Git repository.

## Usage

Run the utility directly:

```bash
py basecamp_thread_export.py
```

The utility will prompt for a Basecamp Classic discussion URL.

Alternatively, supply the URL as an argument:

```bash
py basecamp_thread_export.py "https://customerfx.basecamphq.com/projects/10015594-example/posts/117203208"
```

The utility retrieves the original post and all comments, then creates a text file named:

```text
basecamp_thread_117203208.txt
```

The file is saved in the **current working directory**, not necessarily the directory containing the Python script.

### Running from Anywhere Using Git Bash

To make the utility accessible from any directory, create a launcher named `basecamp` in `~/bin`:

```bash
#!/usr/bin/env bash
py "/c/Path/To/Repository/basecamp_thread_export.py" "$@"
```

Make the launcher executable:

```bash
chmod +x ~/bin/basecamp
```

Ensure `~/bin` is included in your Git Bash PATH:

```bash
export PATH="$HOME/bin:$PATH"
```

This can be added to `~/.bashrc` to make it persistent.

You can now run:

```bash
basecamp
```

Or:

```bash
basecamp "https://customerfx.basecamphq.com/projects/10015594-example/posts/117203208"
```

The resulting file will be created in whichever directory the command was executed from.

## Export Format

The output is a plain-text file containing the original discussion and all comments.

Example:

```text
BASECAMP THREAD
Title: Example Discussion
URL: https://customerfx.basecamphq.com/...

==================================================

ORIGINAL POST
John Smith - October 14, 2026

Original message content...

==================================================

COMMENTS

Jane Doe - October 15, 2026

First response...

--------------------------------------------------

John Smith - October 16, 2026
Via Email: john@example.com

Second response...

Attachments:
- ExampleDocument.docx
  URL: https://customerfx.basecamphq.com/...
```

Attachments are referenced in the export but are not downloaded.

## How It Works

The utility uses the Basecamp Classic API to retrieve discussion content.

It makes two types of requests:

**Original post:**

```text
GET /posts/{post_id}.xml
```

**Comments:**

```text
GET /posts/{post_id}/comments.xml
```

For discussions with more comments than fit in a single API response, the utility follows the `continued-at` attribute returned in the XML until all comments have been retrieved.

The retrieved comments are then sorted by their creation timestamps and combined with the original post.

## Notes

- This utility is intended for Basecamp Classic, not newer versions of Basecamp.
- API access requires a valid authentication token.
- Attachments are listed but not downloaded.
- Exported files may contain confidential client information and should be handled accordingly.
- The utility is read-only and does not modify any Basecamp content.

## API Reference

[Basecamp Classic API Documentation](https://github.com/basecamp/basecamp-classic-api)