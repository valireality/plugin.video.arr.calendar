# -*- coding: utf-8 -*-
"""
plugin.video.arr.calendar
Main entry point for the Kodi addon.

URL routing:
  plugin://plugin.video.arr.calendar/            -> Main menu
  plugin://plugin.video.arr.calendar/?mode=radarr -> Radarr calendar
  plugin://plugin.video.arr.calendar/?mode=sonarr -> Sonarr calendar
"""

import sys
import os
import time
from datetime import datetime, timedelta

try:
    from urllib.parse import parse_qsl, urlencode
except ImportError:
    from urlparse import parse_qsl
    from urllib import urlencode

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

# ---------------------------------------------------------------------------
# Bootstrap: add resources/lib to sys.path
# ---------------------------------------------------------------------------
ADDON       = xbmcaddon.Addon()
ADDON_ID    = ADDON.getAddonInfo("id")
ADDON_PATH  = ADDON.getAddonInfo("path")
PLUGIN_URL  = sys.argv[0]
PLUGIN_HANDLE = int(sys.argv[1])

sys.path.insert(0, os.path.join(ADDON_PATH, "resources", "lib"))

import api  # noqa: E402  (must come after sys.path setup)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _setting(key):
    return ADDON.getSetting(key).strip()


def _setting_int(key, default=0):
    try:
        return int(ADDON.getSetting(key))
    except (ValueError, TypeError):
        return default


def _build_plugin_url(params):
    return "{}?{}".format(PLUGIN_URL, urlencode(params))


def _setting_bool(key):
    try:
        return ADDON.getSetting(key).lower() == "true"
    except Exception:
        return False


def _is_due_date(date_str):
    """True when the given YYYY-MM-DD date is today or in the past."""
    if not date_str:
        xbmc.log("[arrCalendar] _is_due_date: empty date_str", xbmc.LOGINFO)
        return False

    date_only = str(date_str)[:10]
    if len(date_only) != 10:
        xbmc.log("[arrCalendar] _is_due_date: invalid date '{}'".format(date_str), xbmc.LOGINFO)
        return False

    try:
        # YYYY-MM-DD is lexicographically sortable, so string compare is enough.
        today = time.strftime("%Y-%m-%d")
        result = date_only <= today
        xbmc.log(
            "[arrCalendar] _is_due_date: '{}' <= '{}' = {}".format(date_only, today, result),
            xbmc.LOGINFO,
        )
        return result
    except Exception as e:
        xbmc.log("[arrCalendar] _is_due_date exception: {}".format(e), xbmc.LOGERROR)
        return False


def _play_item(path, label):
    xbmc.log(
        "[arrCalendar] _play_item called: path='{}', label='{}'".format(path, label),
        xbmc.LOGINFO,
    )
    
    path_from = _setting("path_map_from")
    path_to = _setting("path_map_to")

    if not path or path == "None":
        xbmcgui.Dialog().ok(
            "Play - No file path",
            "No file path available for '{}'.".format(label or "item"),
        )
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
        return

    play_path = path
    if path_from and path_to and path.startswith(path_from):
        play_path = path_to + path[len(path_from):]

    try:
        import xbmcvfs
        if not xbmcvfs.exists(play_path):
            xbmcgui.Dialog().ok(
                "Play - Path not accessible",
                "Kodi cannot access this path:\n{}\n\n"
                "Set addon path mapping in settings, e.g.\n"
                "from: /volume1\n"
                "to:   smb://NAS/volume1".format(play_path),
            )
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
            return
    except Exception:
        pass

    xbmc.Player().play(play_path)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)


def _trigger_quick_search(target, item_id, label):
    try:
        lookup_id = int(item_id)
    except (TypeError, ValueError):
        xbmcgui.Dialog().notification(
            "Quick Search",
            "Invalid item id for {}".format(label or "item"),
            xbmcgui.NOTIFICATION_ERROR,
            3500,
        )
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
        return

    if target == "radarr":
        if not _setting("radarr_url") or not _setting("radarr_api_key"):
            xbmcgui.Dialog().ok(
                "Radarr - Configuration missing",
                "Please set the Radarr URL and API Key in the addon settings.",
            )
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
            return
        ok = api.quick_search_radarr_movie(
            _setting("radarr_url"),
            _setting("radarr_api_key"),
            lookup_id,
        )
    elif target == "sonarr":
        if not _setting("sonarr_url") or not _setting("sonarr_api_key"):
            xbmcgui.Dialog().ok(
                "Sonarr - Configuration missing",
                "Please set the Sonarr URL and API Key in the addon settings.",
            )
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
            return
        ok = api.quick_search_sonarr_episode(
            _setting("sonarr_url"),
            _setting("sonarr_api_key"),
            lookup_id,
        )
    else:
        xbmcgui.Dialog().notification(
            "Quick Search",
            "Unknown target '{}'".format(target),
            xbmcgui.NOTIFICATION_ERROR,
            3500,
        )
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
        return

    if ok:
        xbmcgui.Dialog().notification(
            "Quick Search",
            "Queued search for {}".format(label or "item"),
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )
    else:
        xbmcgui.Dialog().notification(
            "Quick Search",
            "Failed to queue search for {}".format(label or "item"),
            xbmcgui.NOTIFICATION_ERROR,
            3500,
        )

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)


# ---------------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------------

def _date_range():
    past   = _setting_int("days_past",   1)
    future = _setting_int("days_future", 14)
    today  = datetime.now().date()
    start  = (today - timedelta(days=past)).isoformat()
    end    = (today + timedelta(days=future)).isoformat()
    return start, end


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu():
    items = []
    # Show modules depending on enable flags
    if _setting_bool("enable_radarr"):
        items.append(("Radarr Calendar - Upcoming Movies", {"mode": "radarr"}))
    if _setting_bool("enable_sonarr"):
        items.append(("Sonarr Calendar - Upcoming Episodes", {"mode": "sonarr"}))
    items.append(("Add Shortcuts to Kodi Home Screen", {"mode": "add_shortcuts"}))

    for label, params in items:
        li = xbmcgui.ListItem(label)
        li.setArt({"icon": os.path.join(ADDON_PATH, "resources", "icon.png")})
        url = _build_plugin_url(params)
        xbmcplugin.addDirectoryItem(
            handle=PLUGIN_HANDLE, url=url, listitem=li, isFolder=True
        )

    xbmcplugin.addSortMethod(PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ---------------------------------------------------------------------------
# Home screen shortcuts
# ---------------------------------------------------------------------------

def add_home_shortcuts():
    """Add Radarr & Sonarr shortcuts directly to the Kodi Home Screen
    (the same row as TV, Radio, Games, Weather) using Estuary skin's
    homemenunew slots via built-in skin string/bool setters."""
    icon = "special://home/addons/{}/resources/icon.png".format(ADDON_ID)

    shortcuts = [
        (
            "Radarr - Upcoming Movies",
            "ActivateWindow(Videos,plugin://plugin.video.arr.calendar/?mode=radarr,return)",
            icon,
        ),
        (
            "Sonarr - Upcoming Episodes",
            "ActivateWindow(Videos,plugin://plugin.video.arr.calendar/?mode=sonarr,return)",
            icon,
        ),
    ]

    added = 0
    next_slot = 1  # search for a free homemenunew slot starting here

    for name, action, thumb in shortcuts:
        # Skip if this action is already assigned to any slot (1-8)
        already = any(
            xbmc.getInfoLabel("Skin.String(homemenunew{}action)".format(s)) == action
            for s in range(1, 9)
        )
        if already:
            continue

        # Advance past occupied slots
        while next_slot <= 8 and xbmc.getCondVisibility(
            "Skin.HasSetting(homemenunew{}enabled)".format(next_slot)
        ):
            next_slot += 1

        if next_slot > 8:
            break  # all slots full

        # Set the shortcut data then enable the slot
        xbmc.executebuiltin("Skin.SetString(homemenunew{}name,{})".format(next_slot, name))
        xbmc.executebuiltin("Skin.SetString(homemenunew{}action,{})".format(next_slot, action))
        xbmc.executebuiltin("Skin.SetString(homemenunew{}thumb,{})".format(next_slot, thumb))
        # ToggleSetting turns the slot on (it was confirmed off above)
        xbmc.executebuiltin("Skin.ToggleSetting(homemenunew{}enabled)".format(next_slot))

        next_slot += 1
        added += 1

    if added:
        xbmcgui.Dialog().ok(
            "Shortcuts Added",
            "{} shortcut(s) added to the Home Screen.\n\n"
            "They now appear alongside TV, Radio, Games and Weather.".format(added),
        )
    else:
        xbmcgui.Dialog().notification(
            "Shortcuts",
            "Already on the Home Screen.",
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)
