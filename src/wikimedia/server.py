import asyncio
import aiohttp
from typing import Optional

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import BaseModel
import mcp.server.stdio
import datetime

server = Server("wikimedia")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for Wikimedia operations."""
    return [
        types.Tool(
            name="search_content",
            description="Full-text search across Wikimedia page content. Returns snippets matching the query. Parameters: query (required), limit (1-50), project (e.g., 'wikipedia'), language (e.g., 'en')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_page",
            description="Get Wikimedia page content, title, URL and last modified date. Parameters: title (required), project (e.g., 'wikipedia'), language (e.g., 'en')",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="search_titles",
            description="Search Wikimedia page titles starting with the query. Returns suggestions with descriptions. Parameters: query (required), limit (1-100), project (e.g., 'wikipedia'), language (e.g., 'en')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_languages",
            description="Get versions of a Wikimedia page in other languages. Parameters: title (required), project (e.g., 'wikipedia'), language (e.g., 'en')",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="get_featured",
            description="Get featured Wikimedia content for a date. Returns featured article, most read pages, and picture of the day. Parameters: date (YYYY/MM/DD, default today), project ('wikipedia' only), language (en/de/fr/es/ru/ja/zh)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                }
            }
        ),
        types.Tool(
            name="get_on_this_day",
            description="Get historical events from Wikimedia for a date. Parameters: date (MM/DD, default today), type (all/selected/births/deaths/holidays/events), project ('wikipedia' only), language (en/de/fr/es/ru/ja/zh)",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "type": {"type": "string", "enum": ["all", "selected", "births", "deaths", "holidays", "events"], "default": "all"},
                    "project": {"type": "string", "default": "wikipedia"},
                    "language": {"type": "string", "default": "en"}
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if arguments is None:
        arguments = {}  # Use empty dict instead of raising error

    async with aiohttp.ClientSession() as session:
        try:
            if name == "search_content":
                query = arguments.get("query")
                limit = arguments.get("limit", 10)
                project = arguments.get("project", "wikipedia")
                language = arguments.get("language", "en")
                
                api_url = f"https://api.wikimedia.org/core/v1/{project}/{language}/search/page?q={query}&limit={limit}"
                
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    results = []
                    for page in data.get("pages", []):
                        title = page["title"]
                        description = page.get("description", "")
                        excerpt = page.get("excerpt", "")
                        # Replace HTML search match spans with bold text
                        excerpt = excerpt.replace('<span class="searchmatch">', '**').replace('</span>', '**')
                        
                        results.append(f"# {title}\n\n{description}\n\n{excerpt}")
                    
                    return [
                        types.TextContent(
                            type="text",
                            text="\n\n---\n\n".join(results)
                        )
                    ]
                    
            elif name == "get_page":
                try:
                    title = arguments.get("title")
                    project = arguments.get("project", "wikipedia")
                    language = arguments.get("language", "en")
                    
                    api_url = f"https://{language}.{project}.org/w/api.php"
                    params = {
                        "action": "query",
                        "titles": title,
                        "prop": "revisions|info",
                        "rvprop": "content|timestamp",
                        "rvslots": "main",
                        "format": "json",
                        "redirects": "1",  # Follow redirects
                        "inprop": "url"    # Get final URL after redirects
                    }
                    
                    async with session.get(api_url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        # Extract the page data
                        pages = data.get("query", {}).get("pages", {})
                        if not pages:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Page '{title}' not found"
                                )
                            ]
                        
                        # Get the first (and only) page
                        page = list(pages.values())[0]
                        
                        # Check if page exists
                        if "missing" in page:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Page '{title}' not found"
                                )
                            ]
                        
                        # Get the content and timestamp
                        revision = page["revisions"][0]
                        content = revision["slots"]["main"]["*"]
                        timestamp = revision["timestamp"]
                        
                        # If there was a redirect, get the final title
                        final_title = page["title"]
                        if "redirects" in data["query"]:
                            final_title = data["query"]["redirects"][-1]["to"]
                            
                        # Format the response
                        page_data = {
                            "title": final_title,
                            "content": content,
                            "last_modified": timestamp
                        }
                        
                        return [
                            types.TextContent(
                                type="text",
                                text=f"# {page_data['title']}\n\n{page_data['content']}\n\nLast modified: {page_data['last_modified']}"
                            )
                        ]
                except Exception as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error retrieving page: {str(e)}"
                        )
                    ]

            elif name == "search_titles":
                query = arguments.get("query")
                limit = arguments.get("limit", 10)
                project = arguments.get("project", "wikipedia")
                language = arguments.get("language", "en")
                
                api_url = f"https://api.wikimedia.org/core/v1/{project}/{language}/search/title?q={query}&limit={limit}"
                
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    results = []
                    for page in data.get("pages", []):
                        title = page["title"]
                        description = page.get("description", "")
                        
                        results.append(f"# {title}\n{description}")
                    
                    return [
                        types.TextContent(
                            type="text",
                            text="\n\n---\n\n".join(results)
                        )
                    ]
            
            elif name == "get_languages":
                try:
                    title = arguments.get("title")
                    project = arguments.get("project", "wikipedia")
                    language = arguments.get("language", "en")
                    
                    api_url = f"https://{language}.{project}.org/w/api.php"
                    params = {
                        "action": "query",
                        "titles": title,
                        "prop": "langlinks",
                        "lllimit": "500",
                        "format": "json",
                        "redirects": "1"  # Follow redirects
                    }
                    
                    async with session.get(api_url, params=params) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        # Extract the page data
                        pages = data.get("query", {}).get("pages", {})
                        if not pages:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Page '{title}' not found"
                                )
                            ]
                        
                        # Get the first (and only) page
                        page = list(pages.values())[0]
                        
                        # Check if page exists
                        if "missing" in page:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Page '{title}' not found"
                                )
                            ]
                        
                        if "langlinks" not in page:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No language links found for '{title}'"
                                )
                            ]
                        
                        # Sort language links by language code
                        lang_links = sorted(page["langlinks"], key=lambda x: x["lang"])
                        
                        results = []
                        for lang in lang_links:
                            lang_code = lang["lang"]
                            lang_title = lang["*"]
                            results.append(f"- [{lang_code}] {lang_title}")
                        
                        if not results:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No language links found for '{title}'"
                                )
                            ]
                        
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Found {len(results)} language versions:\n\n" + "\n".join(results)
                            )
                        ]
                except Exception as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error retrieving language links: {str(e)}"
                        )
                    ]
            
            elif name == "get_featured":
                try:
                    project = arguments.get("project", "wikipedia")
                    language = arguments.get("language", "en")
                    date = arguments.get("date")
                    
                    # Featured content is only available for Wikipedia in certain languages
                    if project != "wikipedia":
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Featured content is only available for Wikipedia, not {project}"
                            )
                        ]
                    
                    # Only certain languages have featured content feeds
                    supported_languages = {"en", "de", "fr", "es", "ru", "ja", "zh"}
                    if language not in supported_languages:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Featured content is not available for language '{language}'. Supported languages are: {', '.join(sorted(supported_languages))}"
                            )
                        ]
                    
                    # Use provided date or today
                    if date:
                        try:
                            # Validate date format
                            datetime.datetime.strptime(date, "%Y/%m/%d")
                        except ValueError:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Invalid date format: {date}. Please use YYYY/MM/DD format (e.g., 2025/01/02)"
                                )
                            ]
                    else:
                        date = datetime.datetime.now().strftime("%Y/%m/%d")
                    
                    # Get featured content using the REST API
                    api_url = f"https://api.wikimedia.org/feed/v1/{project}/{language}/featured/{date}"
                    
                    async with session.get(api_url) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        sections = []
                        
                        if "tfa" in data:  # Today's Featured Article
                            tfa = data["tfa"]
                            sections.append(f"# Today's Featured Article\n\n## {tfa.get('title', '')}\n\n{tfa.get('extract', '')}")
                        
                        if "mostread" in data:  # Most Read
                            mostread = data["mostread"]
                            articles = mostread.get("articles", [])[:5]  # Top 5 most read
                            if articles:
                                sections.append("# Most Read Articles\n\n" + "\n\n".join(
                                    f"## {article.get('title', '')}\n{article.get('extract', '')}"
                                    for article in articles
                                ))
                        
                        if "image" in data:  # Picture of the day
                            image = data["image"]
                            sections.append(f"# Picture of the Day\n\n## {image.get('title', '')}\n\n{image.get('description', {}).get('text', '')}")
                        
                        if not sections:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No featured content found for date: {date}"
                                )
                            ]
                        
                        return [
                            types.TextContent(
                                type="text",
                                text="\n\n---\n\n".join(sections)
                            )
                        ]
                except Exception as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error retrieving featured content: {str(e)}"
                        )
                    ]
            
            elif name == "get_on_this_day":
                try:
                    date = arguments.get("date")
                    type_ = arguments.get("type", "all")
                    project = arguments.get("project", "wikipedia")
                    language = arguments.get("language", "en")
                    
                    # Validate event type
                    valid_types = {"all", "selected", "births", "deaths", "holidays", "events"}
                    if type_ not in valid_types:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Invalid event type: '{type_}'. Supported types are: {', '.join(sorted(valid_types))}"
                            )
                        ]
                    
                    # On this day is only available for Wikipedia in certain languages
                    if project != "wikipedia":
                        return [
                            types.TextContent(
                                type="text",
                                text=f"On this day events are only available for Wikipedia, not {project}"
                            )
                        ]
                    
                    # Only certain languages have on this day feeds
                    supported_languages = {"en", "de", "fr", "es", "ru", "ja", "zh"}
                    if language not in supported_languages:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"On this day events are not available for language '{language}'. Supported languages are: {', '.join(sorted(supported_languages))}"
                            )
                        ]
                    
                    if not date:
                        # Use today's date in MM/DD format
                        date = datetime.datetime.now().strftime("%m/%d")
                    
                    # Parse the date to ensure correct format
                    try:
                        month, day = date.split("/")
                        # Ensure month and day are two digits
                        month = month.zfill(2)
                        day = day.zfill(2)
                    except ValueError:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Invalid date format: {date}. Please use MM/DD format (e.g., 01/28)"
                            )
                        ]
                    
                    # Validate month/day
                    month_int = int(month)
                    day_int = int(day)
                    if not (1 <= month_int <= 12):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Invalid month: {month}. Must be between 01 and 12"
                            )
                        ]
                    
                    # Basic validation for days per month
                    days_in_month = {
                        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
                        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
                    }
                    if not (1 <= day_int <= days_in_month[month_int]):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Invalid day: {day}. Month {month} has {days_in_month[month_int]} days"
                            )
                        ]
                        
                    # Use the REST API endpoint with the correct type
                    endpoint = "all" if type_ == "all" else type_
                    api_url = f"https://api.wikimedia.org/feed/v1/{project}/{language}/onthisday/{endpoint}/{month}/{day}"
                    
                    async with session.get(api_url) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        sections = []
                        
                        if type_ == "all" or type_ == "selected":
                            if "selected" in data:
                                events = data["selected"][:10]  # Top 10 selected events
                                sections.append("# Selected Events\n\n" + "\n\n".join(
                                    f"## {event.get('year', '')}\n{event.get('text', '')}"
                                    for event in events
                                ))
                        
                        if type_ == "all" or type_ == "births":
                            if "births" in data:
                                births = data["births"][:5]  # Top 5 births
                                sections.append("# Births\n\n" + "\n\n".join(
                                    f"## {birth.get('year', '')} - {birth.get('text', '')}"
                                    for birth in births
                                ))
                        
                        if type_ == "all" or type_ == "deaths":
                            if "deaths" in data:
                                deaths = data["deaths"][:5]  # Top 5 deaths
                                sections.append("# Deaths\n\n" + "\n\n".join(
                                    f"## {death.get('year', '')} - {death.get('text', '')}"
                                    for death in deaths
                                ))
                        
                        if type_ == "all" or type_ == "holidays":
                            if "holidays" in data:
                                holidays = data["holidays"]
                                sections.append("# Holidays and Observances\n\n" + "\n\n".join(
                                    f"- {holiday.get('text', '')}"
                                    for holiday in holidays
                                ))
                        
                        if not sections:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No {type_} events found for date: {month}/{day}"
                                )
                            ]
                        
                        return [
                            types.TextContent(
                                type="text",
                                text="\n\n---\n\n".join(sections)
                            )
                        ]
                except Exception as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error retrieving historical events: {str(e)}"
                        )
                    ]
            
            raise ValueError(f"Unknown tool: {name}")
            
        except aiohttp.ClientError as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error accessing Wikipedia API: {str(e)}"
                )
            ]
        except ValueError as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Unexpected error: {str(e)}"
                )
            ]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="wikimedia",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())