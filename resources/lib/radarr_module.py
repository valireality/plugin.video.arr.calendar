# -*- coding: utf-8 -*-
"""Radarr module: contains Radarr-specific calendar handler.
This module can be enabled/disabled via addon settings (enable_radarr).
It is imported and called from default.py when enabled.
"""
import os
import sys
from datetime import datetime
try:
    from urllib.parse import urlencode
except Exception:
    from urllib import urlencode

import xbmcgui
import xbmcplugin
import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))
import api


def radarr_calendar(plugin_url, plugin_handle):
    ADDON = xbmcaddon.Addon()
    ADDON_PATH = ADDON.getAddonInfo('path')

    base_url = ADDON.getSetting('radarr_url')
    api_key = ADDON.getSetting('radarr_api_key')

    if not base_url or not api_key:
        xbmcgui.Dialog().ok(
            'Radarr - Configuration missing',
            'Please set the Radarr URL and API Key in the addon settings.'
        )
        xbmcplugin.endOfDirectory(int(plugin_handle), succeeded=False)
        return

    # date range helper in default.py normally; mimic small range default
    from datetime import date, timedelta
    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=14)).isoformat()

    movies = api.get_radarr_calendar(base_url, api_key, start, end)
    if movies is None:
        xbmcgui.Dialog().ok('Radarr - Connection error', 'Could not connect to Radarr.')
        xbmcplugin.endOfDirectory(int(plugin_handle), succeeded=False)
        return

    if not movies:
        li = xbmcgui.ListItem('[No upcoming movies in this period]')
        xbmcplugin.addDirectoryItem(handle=int(plugin_handle), url='', listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(int(plugin_handle))
        return

    movies.sort(key=lambda m: (m.get('digitalRelease') or m.get('physicalRelease') or m.get('inCinemas') or ''))

    for movie in movies:
        item = api.extract_radarr_item(movie)
        date_str = item['release_date'] or '?'
        title_with_date = '{} ({}) - {}'.format(item['title'], item['year'], date_str)
        label = title_with_date + ('  [Downloaded]' if item.get('has_file') else '')
        li = xbmcgui.ListItem(label)
        try:
            tag = li.getVideoInfoTag()
            tag.setTitle(title_with_date)
        except AttributeError:
            li.setInfo('video', {'title': title_with_date})

        if item.get('poster'):
            li.setArt({'thumb': item.get('poster'), 'poster': item.get('poster')})

        url = ''
        if item.get('has_file') and item.get('file_path'):
            url = '{}?mode=play&path={}&label={}'.format(plugin_url, item.get('file_path'), item.get('title'))

        xbmcplugin.addDirectoryItem(handle=int(plugin_handle), url=url, listitem=li, isFolder=False)

    xbmcplugin.addSortMethod(int(plugin_handle), xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(int(plugin_handle))