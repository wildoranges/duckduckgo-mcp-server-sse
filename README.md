# DuckDuckGo Search MCP Server (SSE)

A Model Context Protocol (MCP) server that provides web search capabilities through DuckDuckGo, with additional features for content fetching and parsing, running over HTTP (SSE).

## Features

- **Web Search**: Search DuckDuckGo with advanced rate limiting and result formatting
- **Content Fetching**: Retrieve and parse webpage content with intelligent text extraction
- **Rate Limiting**: Built-in protection against rate limits for both search and content fetching
- **Error Handling**: Comprehensive error handling and logging
- **LLM-Friendly Output**: Results formatted specifically for large language model consumption

## Usage

### Startup

To manage this project, it's better to use [uv](https://docs.astral.sh/uv/getting-started/installation/).

1. Clone this repository
```bash
git clone https://github.com/wildoranges/duckduckgo-mcp-server-sse
cd duckduckgo-mcp-server-sse
```
2. Start the server (One-time execution)
```bash
uv run python src/duckduckgo_mcp_server/server.py
```
3. Or, you can create a venv to run
```
uv sync
source .venv/bin/activate
python src/duckduckgo_mcp_server/server.py
```
4. You can modify [server.py](src/duckduckgo_mcp_server/server.py) to change the host and port. default is `0.0.0.0:18000`.

### Settings in CLINE

Add the following configuration:

```json
{
    "mcpServers": {
        "ddg-search-sse": {
            "disabled": false,
            "timeout": 60,
            "type": "sse",
            "url": "http://0.0.0.0:18000/sse",
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
