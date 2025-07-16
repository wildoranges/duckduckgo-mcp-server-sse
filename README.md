# DuckDuckGo Search MCP Server (SSE)

A Model Context Protocol (MCP) server that provides web search capabilities through DuckDuckGo, with additional features for content fetching and parsing, running over HTTP (SSE).

## Features

- **Web Search**: Search DuckDuckGo with advanced rate limiting and result formatting
- **Content Fetching**: Retrieve and parse webpage content with intelligent text extraction
- **Rate Limiting**: Built-in protection against rate limits for both search and content fetching
- **Error Handling**: Comprehensive error handling and logging
- **LLM-Friendly Output**: Results formatted specifically for large language model consumption

## Usage

### Installation

You can install the server using pip:

```bash
pip install duckduckgo-mcp-server-sse
```

### Startup

You can start the server using the following command:

```bash
duckduckgo-mcp-server-sse --host <your-host> --port <your-port>
```

- `--host`: The host to bind the server to. Defaults to `0.0.0.0`.
- `--port`: The port to run the server on. Defaults to `8000`.

For example:

```bash
duckduckgo-mcp-server-sse --host 127.0.0.1 --port 8080
```

### Settings in CLINE

Add the following configuration, adjusting the host and port to match your server setup:

```json
{
    "mcpServers": {
        "ddg-search-sse": {
            "disabled": false,
            "timeout": 60,
            "type": "sse",
            "url": "http://127.0.0.1:8000/sse",
            "headers": {
                "Accept": "application/json, text/event-stream"
            }
        }
    }
}
```

## Available Tools

### 1. Search Tool

```python
async def search(query: str, max_results: int = 10) -> str
```

Performs a web search on DuckDuckGo and returns formatted results.

**Parameters:**
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10)

**Returns:**
Formatted string containing search results with titles, URLs, and snippets.

### 2. Content Fetching Tool

```python
async def fetch_content(url: str) -> str
```

Fetches and parses content from a webpage.

**Parameters:**
- `url`: The webpage URL to fetch content from

**Returns:**
Cleaned and formatted text content from the webpage.

## Features in Detail

### Rate Limiting

- Search: Limited to 30 requests per minute
- Content Fetching: Limited to 20 requests per minute
- Automatic queue management and wait times

### Result Processing

- Removes ads and irrelevant content
- Cleans up DuckDuckGo redirect URLs
- Formats results for optimal LLM consumption
- Truncates long content appropriately

### Error Handling

- Comprehensive error catching and reporting
- Detailed logging through MCP context
- Graceful degradation on rate limits or timeouts

## Contributing

Issues and pull requests are welcome! Some areas for potential improvement:

- Additional search parameters (region, language, etc.)
- Enhanced content parsing options
- Caching layer for frequently accessed content
- Additional rate limiting strategies

## License

This project is licensed under the MIT License.
