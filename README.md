# Wikimedia MCP Server

A Model Context Protocol (MCP) server for interacting with Wikimedia APIs. Access Wikipedia and other Wikimedia project content programmatically with natural language queries.

## Features

- **Search Content**: Full-text search across Wikimedia page content
- **Search Titles**: Search page titles with autocomplete suggestions
- **Get Page**: Retrieve page content, title, URL and metadata
- **Language Versions**: Find versions of a page in other languages
- **Featured Content**: Get featured articles, most read pages, and pictures of the day
- **Historical Events**: Get events, births, deaths, and holidays for any date

## Requirements

- Python 3.12+
- uv package manager
- MCP server framework

## Security

- All user inputs are validated
- No sensitive data or credentials required
- Rate limiting handled by Wikimedia API
- Error messages don't expose internal details

## Installation

### Claude Desktop Configuration

On MacOS:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

On Windows:
```
C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json
```

### Development Configuration
```json
{
  "mcpServers": {
    "wikimedia": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\MCP\\server\\community\\wikimedia",
        "run",
        "wikimedia"
      ]
    }
  }
}
```

### Published Configuration
```json
{
  "mcpServers": {
    "wikimedia": {
      "command": "uvx",
      "args": [
        "wikimedia"
      ]
    }
  }
}
```

## Tools

### search_content
Full-text search across Wikimedia page content. Returns snippets matching the query.
- `query` (required): Search term
- `limit` (1-50, default 10): Number of results
- `project` (default "wikipedia"): Wikimedia project
- `language` (default "en"): Language code

### search_titles
Search Wikimedia page titles starting with the query. Returns suggestions with descriptions.
- `query` (required): Search prefix
- `limit` (1-100, default 10): Number of results
- `project` (default "wikipedia"): Wikimedia project
- `language` (default "en"): Language code

### get_page
Get Wikimedia page content, title, URL and last modified date.
- `title` (required): Page title
- `project` (default "wikipedia"): Wikimedia project
- `language` (default "en"): Language code

### get_languages
Get versions of a Wikimedia page in other languages.
- `title` (required): Page title
- `project` (default "wikipedia"): Wikimedia project
- `language` (default "en"): Language code

### get_featured
Get featured Wikimedia content for a date. Returns featured article, most read pages, and picture of the day.
- `date` (YYYY/MM/DD, default today): Date to get content for
- `project` ("wikipedia" only): Must be Wikipedia
- `language` (en/de/fr/es/ru/ja/zh): Supported languages

### get_on_this_day
Get historical events from Wikimedia for a date.
- `date` (MM/DD, default today): Date to get events for
- `type` (default "all"): Event type - all/selected/births/deaths/holidays/events
- `project` ("wikipedia" only): Must be Wikipedia
- `language` (en/de/fr/es/ru/ja/zh): Supported languages

## Example Usage

```python
# Search for content about "artificial intelligence"
result = await client.call_tool("search_content", {
    "query": "artificial intelligence",
    "limit": 5,
    "language": "en"
})

# Get today's featured content
result = await client.call_tool("get_featured", {
    "language": "en"
})

# Get historical events for January 1st
result = await client.call_tool("get_on_this_day", {
    "date": "01/01",
    "type": "all",
    "language": "en"
})
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT License. See [LICENSE](LICENSE) file for details.