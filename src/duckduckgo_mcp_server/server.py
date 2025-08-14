from mcp.server.fastmcp import FastMCP, Context
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import urllib.parse
import sys
import traceback
import asyncio
from datetime import datetime, timedelta
import time
import re
import argparse
import signal
from scholarly import scholarly, ProxyGenerator
import logging
import json


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str
    position: int


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            # Wait until we can make another request
            wait_time = 60 - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        self.requests.append(now)


class DuckDuckGoSearcher:
    BASE_URL = "https://html.duckduckgo.com/html"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.rate_limiter = RateLimiter()

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query. This could be due to DuckDuckGo's bot detection or the query returned no matches. Please try rephrasing your search or try again in a few minutes."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.position}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)

    async def search(
        self, query: str, ctx: Context, max_results: int = 10
    ) -> List[SearchResult]:
        try:
            # Apply rate limiting
            await self.rate_limiter.acquire()

            # Create form data for POST request
            data = {
                "q": query,
                "b": "",
                "kl": "",
            }

            await ctx.info(f"Searching DuckDuckGo for: {query}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.BASE_URL, data=data, headers=self.HEADERS, timeout=30.0
                )
                response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, "html.parser")
            if not soup:
                await ctx.error("Failed to parse HTML response")
                return []

            results = []
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                if not title_elem:
                    continue

                link_elem = title_elem.find("a")
                if not link_elem:
                    continue

                title = link_elem.get_text(strip=True)
                link = link_elem.get("href", "")

                # Skip ad results
                if "y.js" in link:
                    continue

                # Clean up DuckDuckGo redirect URLs
                if link.startswith("//duckduckgo.com/l/?uddg="):
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])

                snippet_elem = result.select_one(".result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(
                    SearchResult(
                        title=title,
                        link=link,
                        snippet=snippet,
                        position=len(results) + 1,
                    )
                )

                if len(results) >= max_results:
                    break

            await ctx.info(f"Successfully found {len(results)} results")
            return results

        except httpx.RequestError as e:
            await ctx.error(f"An HTTP request error occurred: {str(e)}")
            return []
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred: {str(e)}")
            return []
        except Exception as e:
            await ctx.error(f"Unexpected error during search: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    async def fetch_and_parse(self, url: str, ctx: Context) -> str:
        """Fetch and parse content from a webpage"""
        try:
            await self.rate_limiter.acquire()

            await ctx.info(f"Fetching content from: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()

            # Get the text content
            text = soup.get_text()

            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text).strip()

            # Truncate if too long
            if len(text) > 8000:
                text = text[:8000] + "... [content truncated]"

            await ctx.info(
                f"Successfully fetched and parsed content ({len(text)} characters)"
            )
            return text

        except httpx.RequestError as e:
            await ctx.error(f"An HTTP request error occurred while fetching {url}: {str(e)}")
            return f"Error: An HTTP request error occurred while fetching the webpage ({str(e)})"
        except httpx.HTTPError as e:
            await ctx.error(f"HTTP error occurred while fetching {url}: {str(e)}")
            return f"Error: Could not access the webpage ({str(e)})"
        except Exception as e:
            await ctx.error(f"Error fetching content from {url}: {str(e)}")
            return f"Error: An unexpected error occurred while fetching the webpage ({str(e)})"


class ScholarSearcher:
    def __init__(self):
        # Proxy setup is now handled within the search method to ensure thread safety
        pass

    def format_results_for_llm(self, results: List[Dict], format: str = "bibtex") -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query on Google Scholar."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        if format == "text":
            for i, result in enumerate(results):
                output.append(f"{i+1}. {result.get('bib', {}).get('title', 'N/A')}")
                output.append(f"   Authors: {', '.join(result.get('bib', {}).get('author', []))}")
                output.append(f"   Venue: {result.get('bib', {}).get('venue', 'N/A')}")
                output.append(f"   Year: {result.get('bib', {}).get('pub_year', 'N/A')}")
                output.append(f"   URL: {result.get('pub_url', 'N/A')}")
                output.append(f"Abstract:\n{result.get('bib', {}).get('abstract', 'N/A')}")
                output.append("")
        else:  # bibtex format
            for i, result in enumerate(results):
                output.append(f"{i+1}. {result.get('bib', {}).get('title', 'N/A')}")
                output.append(f"{result.get('bibtex', {})}")
                output.append("")

        return "\n".join(output)

    async def search(self, query: str, ctx: Context, max_results: int = 10, year_low: Optional[int] = None, year_high: Optional[int] = None, sort_by: str = 'relevance', start_index: int = 0) -> List[Dict]:
        try:
            await ctx.info(f"Searching Google Scholar for: {query}")
            
            async def search_with_limit():
                results = []
                try:
                    search_results_iterator = scholarly.search_pubs(query=query, year_low=year_low, year_high=year_high, sort_by=sort_by, start_index=start_index)
                    for i, pub in enumerate(search_results_iterator):
                        if len(results) >= max_results:
                            break
                        await asyncio.sleep(0.5) # Sleep to avoid rate limiting 
                        bibtex = scholarly.bibtex(pub)
                        pub['bibtex'] = bibtex
                        results.append(pub)
                except Exception as e:
                    await ctx.error(f"Failed to fetch bib content for query {query}: {str(e)}, the search results may be incomplete")
                    return results
                    
                return results

            results = await search_with_limit()

            await ctx.info(f"Successfully found {len(results)} results on Google Scholar")
            return results
        except Exception as e:
            await ctx.error(f"Unexpected error during Scholar search: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            return []

# Initialize FastMCP server
mcp = FastMCP("ddg-search-sse")
searcher = DuckDuckGoSearcher()
fetcher = WebContentFetcher()
scholar_searcher = ScholarSearcher()


@mcp.tool()
async def search(query: str, ctx: Context, max_results: int = 10) -> str:
    """
    Search DuckDuckGo and return formatted results.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        ctx: MCP context for logging
    """
    try:
        results = await searcher.search(query, ctx, max_results)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@mcp.tool()
async def fetch_content(url: str, ctx: Context) -> str:
    """
    Fetch and parse content from a webpage URL.

    Args:
        url: The webpage URL to fetch content from
        ctx: MCP context for logging
    """
    return await fetcher.fetch_and_parse(url, ctx)


@mcp.tool()
async def scholar_search(query: str, ctx: Context, max_results: int = 10, year_low: Optional[int] = None, year_high: Optional[int] = None, sort_by: str = 'relevance', start_index: int = 0, format: str = "bibtex") -> str:
    """
    Search Google Scholar and return formatted results.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
        year_low: Minimum year of publication (default: None)
        year_high: Maximum year of publication (default: None)
        sort_by: 'relevance' or 'date' (default: relevance)
        start_index: Starting index of list of publications (default: 0)
        format: Output format, either 'text' or 'bibtex' (default: bibtex)
        ctx: MCP context for logging
    """
    try:
        results = await scholar_searcher.search(query, ctx, max_results, year_low, year_high, sort_by, start_index)
        return scholar_searcher.format_results_for_llm(results, format)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching Google Scholar: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="DuckDuckGo MCP Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on.",
    )
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
