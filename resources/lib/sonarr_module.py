# -*- coding: utf-8 -*-
"""Sonarr module: contains Sonarr-specific calendar handler.
This module can be enabled/disabled via addon settings (enable_sonarr).
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


def sonarr_calendar(plugin_url, plugin_handle):
    ADDON = xbmcaddon.Addon()
    ADDON_PATH = ADDON.getAddonInfo('path')

    base_url = ADDON.getSetting('sonarr_url')
    api_key = ADDON.getSetting('sonarr_api_key')

    if not base_url or not api_key:
        xbmcgui.Dialog().ok(
            'Sonarr - Configuration missing',
            'Please set the Sonarr URL and API Key in the addon settings.'
        )
        xbmcplugin.endOfDirectory(int(plugin_handle), succeeded=False)
        return

    from datetime import date, timedelta
    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=14)).isoformat()

    episodes = api.get_sonarr_calendar(base_url, api_key, start, end)
    if episodes is None:
        xbmcgui.Dialog().ok('Sonarr - Connection error', 'Could not connect to Sonarr.')
        xbmcplugin.endOfDirectory(int(plugin_handle), succeeded=False)
        return

    if not episodes:
        li = xbmcgui.ListItem('[No upcoming episodes in this period]')
        xbmcplugin.addDirectoryItem(handle=int(plugin_handle), url='', listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(int(plugin_handle))
        return

    episodes.sort(key=lambda e: e.get('airDate') or '')

    for episode in episodes:
        item = api.extract_sonarr_item(episode)
        date_str = item['air_date'] or '?'
        title_with_date = '{} - {}'.format(item['label'], date_str)
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
            url = '{}?mode=play&path={}&label={}'.format(plugin_url, item.get('file_path'), item.get('label'))

        xbmcplugin.addDirectoryItem(handle=int(plugin_handle), url=url, listitem=li, isFolder=False)

    xbmcplugin.addSortMethod(int(plugin_handle), xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(int(plugin_handle))