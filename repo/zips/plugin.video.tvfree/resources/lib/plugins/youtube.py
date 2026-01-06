import json
import xbmc
import xbmcgui
from ..DI import DI
from ..modules.tools import m
from ..plugin import Plugin


class Youtube(Plugin):
    name = "play with youtube"
    priority = 120
    
    def get_list(self, url):
        if "youtube.com" in url or 'plugin.video.youtube' in url :
            next_page = ""
            if "|next_page=" in url:
                next_page = url.split("|next_page=")[1]
                url = url.split("|next_page=")[0]
            url2 = swap_link(url)
            if "/channel/" in url2 or "playlist?list" in url2:
                r = DI.session.get("https://api.youtubemultidownloader.com/playlist", params={"url": url2, "nextPageToken": next_page}, headers=m.headers).text
                r = json.dumps(json.loads(r), indent=4)
                return "youtube://" + r

    def parse_list(self, url, response):
        if "|next_page=" in url:
            url = url.split("|next_page=")[0]
        items = []
        if str(response).startswith("youtube://"):
            r = json.loads(response[10:])
            for item in r["items"]:
                jen_data = {
                    "title": item["title"],
                    "thumbnail": item["thumbnails"].replace("default", "hqdefault"),
                    "fanart": item["thumbnails"].replace("default", "hqdefault"),
                    "summary": item["title"],
                    "link": item["url"],
                    "duration": item["duration"],
                    "type": "item"
                }
                items.append(jen_data)
                
            if r.get("nextPageToken") is not None:
                jen_data = {
                    "title": "Next Page",
                    "thumbnail": "",
                    "fanart": "",
                    "summary": "Next Page",
                    "link": f'{url}|next_page={r["nextPageToken"]}',
                    "type": "dir"
                }
                items.append(jen_data)
            return items

    def play_video(self, video):
        title = video.get('title', '')
        link = video.get('link', '')
        if "youtube" in link or "youtu.be" in link:
            parts = link.split("/")
            video_id = parts[-1].split('=')[-1]
            link = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
            liz = xbmcgui.ListItem(title, path=link)
            xbmc.Player().play(link, listitem=liz)
            return True


def swap_link(link: str):
    _id = ''
    pl_base = 'https://www.youtube.com/playlist?list=' 
    ch_base = 'https://www.youtube.com/channel/'
    vid_base = 'https://www.youtube.com/watch?v='
    args = DI.plugin.args
    
    if '=' in link:
        _id = link.split('=')[-1]
    else:
        _id = link.split('/')[-1]
        
    if 'list' in args:
        new_link = pl_base + args['list'][0]
    elif '/playlist' in link:
        new_link = pl_base + _id
    elif _id.startswith('@'):
        import re
        r = DI.session.get(link, headers=m.headers).text
        _id = re.compile('"browseId":"(.+?)"').findall(r)[0]
        new_link = ch_base + _id
    elif '/channel' in link:
        new_link = ch_base + _id  
    elif '/watch' in link:   
        new_link = vid_base + _id
    else :
        new_link = link
    return new_link