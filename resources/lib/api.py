# -*- coding: utf-8 -*-
"""
Radarr & Sonarr REST API helpers.
Compatible with Radarr v3/v4 and Sonarr v3/v4.
"""

import json
try:
    # Python 3 (Kodi 19 Leia+)
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
    from urllib.parse import urlencode
except ImportError:
    # Python 2 (older Kodi)
    from urllib2 import urlopen, Request, URLError, HTTPError
    from urllib import urlencode

import xbmc


def _build_url(base_url, endpoint, params):
    """Construct a full API URL with query parameters."""
    base_url = base_url.rstrip("/")
    query = urlencode(params)
    return "{}/api/v3/{}?{}".format(base_url, endpoint, query)


def _get(url, api_key):
    """
    Perform an authenticated GET request and return the parsed JSON list/dict.
    Returns None on any error (logs the error via xbmc.log).
    """
    req = Request(url)
    req.add_header("X-Api-Key", api_key)
    req.add_header("Accept", "application/json")
    try:
        response = urlopen(req, timeout=15)
        raw = response.read()
        return json.loads(raw)
    except HTTPError as exc:
        xbmc.log(
            "[arrCalendar] HTTP error {} for URL: {}".format(exc.code, url),
            xbmc.LOGERROR,
        )
    except URLError as exc:
        xbmc.log(
            "[arrCalendar] URL error '{}' for URL: {}".format(exc.reason, url),
            xbmc.LOGERROR,
        )
    except Exception as exc:
        xbmc.log(
            "[arrCalendar] Unexpected error '{}' for URL: {}".format(exc, url),
            xbmc.LOGERROR,
        )
    return None


def _post(base_url, endpoint, api_key, payload):
    """Perform an authenticated POST request and return parsed JSON dict/list."""
    url = "{}/api/v3/{}".format(base_url.rstrip("/"), endpoint)
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data)
    req.add_header("X-Api-Key", api_key)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    try:
        response = urlopen(req, timeout=15)
        raw = response.read()
        return json.loads(raw) if raw else {}
    except HTTPError as exc:
        xbmc.log(
            "[arrCalendar] HTTP POST error {} for URL: {}".format(exc.code, url),
            xbmc.LOGERROR,
        )
    except URLError as exc:
        xbmc.log(
            "[arrCalendar] URL POST error '{}' for URL: {}".format(exc.reason, url),
            xbmc.LOGERROR,
        )
    except Exception as exc:
        xbmc.log(
            "[arrCalendar] Unexpected POST error '{}' for URL: {}".format(exc, url),
            xbmc.LOGERROR,
        )
    return None


# ---------------------------------------------------------------------------
# Radarr
# ---------------------------------------------------------------------------

def get_radarr_calendar(base_url, api_key, start_date, end_date):
    """
    Fetch Radarr calendar.

    Args:
        base_url  (str): e.g. "http://localhost:7878"
        api_key   (str): Radarr API key
        start_date (str): ISO date string "YYYY-MM-DD"
        end_date   (str): ISO date string "YYYY-MM-DD"

    Returns:
        list[dict] | None
    """
    params = {
        "start": start_date,
        "end": end_date,
        "unmonitored": "false",
        "includeMovie": "true",
    }
    url = _build_url(base_url, "calendar", params)
    xbmc.log("[arrCalendar] Radarr request: {}".format(url), xbmc.LOGDEBUG)
    return _get(url, api_key)


def extract_radarr_item(movie):
    """
    Extract a display-friendly dict from a Radarr movie object.
    Priority for release date: digitalRelease > physicalRelease > inCinemas.
    """
    title = movie.get("title", "Unknown")
    year  = movie.get("year", "")

    release_date = (
        movie.get("digitalRelease")
        or movie.get("physicalRelease")
        or movie.get("inCinemas")
        or ""
    )
    if release_date:
        release_date = release_date[:10]  # keep YYYY-MM-DD only

    overview   = movie.get("overview", "")
    studio     = movie.get("studio", "")
    runtime    = movie.get("runtime", 0)
    ratings    = movie.get("ratings", {})
    tmdb_score = ratings.get("tmdb", {}).get("value", 0)
    has_file   = movie.get("hasFile", False)
    movie_id   = movie.get("id")
    movie_file = movie.get("movieFile", {}) if isinstance(movie.get("movieFile", {}), dict) else {}
    file_path  = movie_file.get("path", "")
    
    xbmc.log(
        "[arrCalendar] extract_radarr_item '{}': hasFile={}, file_path='{}'".format(
            title, has_file, file_path
        ),
        xbmc.LOGINFO,
    )

    # Poster image
    poster = ""
    for img in movie.get("images", []):
        if img.get("coverType") == "poster":
            poster = img.get("remoteUrl") or img.get("url") or ""
            break

    # Fanart
    fanart = ""
    for img in movie.get("images", []):
        if img.get("coverType") == "fanart":
            fanart = img.get("remoteUrl") or img.get("url") or ""
            break

    return {
        "title":        title,
        "year":         year,
        "release_date": release_date,
        "overview":     overview,
        "studio":       studio,
        "runtime":      runtime,
        "rating":       tmdb_score,
        "has_file":     has_file,
        "movie_id":     movie_id,
        "file_path":    file_path,
        "poster":       poster,
        "fanart":       fanart,
    }


def quick_search_radarr_movie(base_url, api_key, movie_id):
    """Trigger Radarr movie search command for a specific movie id."""
    payload = {"name": "MoviesSearch", "movieIds": [int(movie_id)]}
    result = _post(base_url, "command", api_key, payload)
    return bool(result)


# ---------------------------------------------------------------------------
# Sonarr
# ---------------------------------------------------------------------------


def get_sonarr_calendar(base_url, api_key, start_date, end_date):
    """
    Fetch Sonarr calendar.

    Args:
        base_url   (str): e.g. "http://localhost:8989"
        api_key    (str): Sonarr API key
        start_date (str): ISO date string "YYYY-MM-DD"
        end_date   (str): ISO date string "YYYY-MM-DD"

    Returns:
        list[dict] | None
    """
    params = {
        "start":        start_date,
        "end":          end_date,
        "unmonitored":  "false",
        "includeSeries":"true",
    }
    url = _build_url(base_url, "calendar", params)
    xbmc.log("[arrCalendar] Sonarr request: {}".format(url), xbmc.LOGDEBUG)
    return _get(url, api_key)


def extract_sonarr_item(episode):
    """
    Extract a display-friendly dict from a Sonarr episode object.
    """
    series      = episode.get("series", {})
    series_title= series.get("title", "Unknown Series")
    ep_title    = episode.get("title", "")
    season_num  = episode.get("seasonNumber", 0)
    ep_num      = episode.get("episodeNumber", 0)
    air_date    = episode.get("airDate", "")
    overview    = episode.get("overview", "")
    has_file    = episode.get("hasFile", False)
    runtime     = series.get("runtime", 0)
    network     = series.get("network", "")
    episode_id  = episode.get("id")
    ep_file     = episode.get("episodeFile", {}) if isinstance(episode.get("episodeFile", {}), dict) else {}
    file_path   = ep_file.get("path", "")

    label = "{}  S{:02d}E{:02d}{}".format(
        series_title,
        season_num,
        ep_num,
        " - {}".format(ep_title) if ep_title else "",
    )
    
    xbmc.log(
        "[arrCalendar] extract_sonarr_item '{}': hasFile={}, file_path='{}'".format(
            label, has_file, file_path
        ),
        xbmc.LOGINFO,
    )

    # Series poster
    poster = ""
    for img in series.get("images", []):
        if img.get("coverType") == "poster":
            poster = img.get("remoteUrl") or img.get("url") or ""
            break

    # Series fanart
    fanart = ""
    for img in series.get("images", []):
        if img.get("coverType") == "fanart":
            fanart = img.get("remoteUrl") or img.get("url") or ""
            break

    return {
        "label":        label,
        "series_title": series_title,
        "ep_title":     ep_title,
        "season":       season_num,
        "episode":      ep_num,
        "air_date":     air_date,
        "overview":     overview,
        "has_file":     has_file,
        "episode_id":   episode_id,
        "file_path":    file_path,
        "runtime":      runtime,
        "network":      network,
        "poster":       poster,
        "fanart":       fanart,
    }


def quick_search_sonarr_episode(base_url, api_key, episode_id):
    """Trigger Sonarr episode search command for a specific episode id."""
    payload = {"name": "EpisodeSearch", "episodeIds": [int(episode_id)]}
    result = _post(base_url, "command", api_key, payload)
    return bool(result)
