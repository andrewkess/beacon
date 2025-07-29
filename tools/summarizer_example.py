import asyncio
import json
import logging
from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiolimiter import AsyncLimiter

# Configure logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Request rate and concurrency
API_MAX_CONCURRENT_REQUESTS = 1
API_RPS = 1
API_RATE_LIMIT = AsyncLimiter(API_RPS, 1)
API_TIMEOUT = 20

# Brave Search API Key
API_KEY = "BSAsCIPqaPLhXXcAs1ysPXNIWhVP0gw"

# Brave Search API host
API_HOST = "https://api.search.brave.com"

# Brave Search API subpaths
API_PATH = {
    "web": urljoin(API_HOST, "res/v1/web/search"),
    "summarizer_search": urljoin(API_HOST, "res/v1/summarizer/search"),
}

# Create request headers for specific endpoints
API_HEADERS = {
    "web": {"X-Subscription-Token": API_KEY, "Api-Version": "2023-10-11"},
    "summarizer": {"X-Subscription-Token": API_KEY, "Api-Version": "2024-04-23"},
}

# Create web search request params
API_PARAMS_WEB = {
    # "q": "what is the second highest mountain",
    "q": "Ukraine war classification evolution",

    "summary": 1,
}


async def get_summary(session: ClientSession) -> None:
    # Fetch web search results so we can get a summary key
    async with session.get(
        API_PATH["web"],
        params=API_PARAMS_WEB,
        headers=API_HEADERS["web"],
    ) as response:
        log.debug("Querying url: [%s]", response.url)
        # print(await response.text())
        data = await response.json()
        status = response.status

    if status != 200:
        log.error(
            "Failure getting web search results \n%s",
            json.dumps(data, indent=2),
        )
        return

    # Get the summary key from web search results
    summary_key = data.get("summarizer", {}).get("key")

    if not summary_key:
        log.error("Failure: Getting summary key")
        return

    log.debug("Summarizer Key: [%s]", summary_key)

    # Fetch summary all in one
    log.debug("Requesting summarizer search in blocking mode")
    async with session.get(
        url=API_PATH["summarizer_search"],
        params={"key": summary_key, "entity_debug": 1},
        headers=API_HEADERS["summarizer"],
    ) as response:
        log.debug("Querying url: [%s]", response.url)
        data = await response.json()
        status = response.status

        log.debug(json.dumps(data, indent=2))


async def main():
    async with API_RATE_LIMIT:
        async with ClientSession(
            connector=TCPConnector(limit=API_MAX_CONCURRENT_REQUESTS),
            timeout=ClientTimeout(API_TIMEOUT),
        ) as session:
            await get_summary(session=session)


asyncio.run(main())
