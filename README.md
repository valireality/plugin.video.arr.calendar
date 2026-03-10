
arr Calendar
===========

Simple README for the Kodi addon `arr Calendar`.

What is this?
- A Kodi addon that shows upcoming movies from Radarr and upcoming TV episodes from Sonarr.

Installation
- Place the `plugin.video.arr.calendar` folder into Kodi's addons directory.
- Restart Kodi if the addon does not appear immediately.

Configuration
- Open the addon settings and provide the following:
  - `radarr_url` and `radarr_api_key` for Radarr
  - `sonarr_url` and `sonarr_api_key` for Sonarr
- Set `days_past` and `days_future` to control the date range.
- If playback files are on remote storage (NAS), use `path_map_from` and `path_map_to` to map paths.

Usage
- From the addon's main menu choose `Radarr Calendar` or `Sonarr Calendar`.
- The list shows the date and title; if a local file is available, you can play it.
- You can add shortcuts to the Kodi Home screen via the menu option.

Troubleshooting
- If no items appear, check the Radarr/Sonarr URL and API key and network access from Kodi.
- If playback fails, verify `path_map_from`/`path_map_to` and whether Kodi can access the path (xbmcvfs).
- The addon uses the `/api/v3/` API path; confirm your Radarr/Sonarr version uses this path.

Note
- This is a minimal README. I can add examples, debugging tips, or implement improvements (for example, adding routing in `default.py`) if you want.

