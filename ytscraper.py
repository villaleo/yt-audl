import urllib.parse
from typing import TypedDict

import requests

YT_BASE_URL = "https://www.youtube.com"
YT_SEARCH_URL = f"{YT_BASE_URL}/results"
YT_WATCH_URL = f"{YT_BASE_URL}/watch"

REQUEST_DELAY_SEC = 1.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def buildSearchUrl(query: str) -> str:
    """
    Encode a query string into a YouTube search URL.

    urllib.parse.urlencode turns {"search_query": "foo bar"} into
    "search_query=foo+bar", which is then appended as a query string.
    """
    params = urllib.parse.urlencode({"search_query": query})
    return f"{YT_SEARCH_URL}?{params}"


def fetchHtml(url: str) -> str:
    """
    Perform a GET request and return the response body as a string.
    Raises requests.HTTPError on 4xx/5xx responses.
    """
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    return response.text


def extractFirstVideoUrl(search_html: str) -> str | None:
    """
    Parse a YouTube search results page and return the URL of the first
    video result.

    Searches through the HTML using a regular expression to search for
    the first object that contains the `watchEndpoint:videoId` key.
    """
    from re import search

    VIDEO_ID_PATTERN = '"watchEndpoint":{"videoId":"'
    AVG_VIDEO_ID_LENGTH = 35

    if res := search(VIDEO_ID_PATTERN, search_html):
        _, start = res.span()
        sliced = search_html[start : start + AVG_VIDEO_ID_LENGTH]
        end = start + sliced.index('"')

        #
        #   search_html:
        #   "...\"watchEndpoint\":{\"videoId\": \"some-videoId\",..."
        #        ^                               ^             ^
        #        _                             start          end

        video_id = search_html[start:end]
        return f"{YT_WATCH_URL}?v={video_id}"

    return None  # no video link found


class FetchResult(TypedDict):
    query: str
    video_url: str | None
    error: str | None


def fetchVideoUrl(query: str) -> FetchResult:
    """
    Searches YouTube and to fetch the first result's video URL.

    Returns a fetch result:
        {
            "query":     the original search string,
            "video_url": the URL of the first result (or None),
            "error":     an error message if something went wrong,
        }
    """
    result: FetchResult = {
        "query": query,
        "video_url": None,
        "error": None,
    }

    print(f"fetching video url for '{query}'")
    try:
        search_url = buildSearchUrl(query)
        search_html = fetchHtml(search_url)

        video_url = extractFirstVideoUrl(search_html)
        if video_url is None:
            result["error"] = "extract: couldn't find a videoId key."
            return result

        result["video_url"] = video_url

    except requests.RequestException as error:
        result["error"] = str(error)

    return result
