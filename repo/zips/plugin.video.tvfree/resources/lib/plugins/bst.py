import re
import sys
from urllib.parse import urljoin
from typing import Optional, List, Dict
import xbmc
import xbmcgui
from bs4 import BeautifulSoup
from ..modules.tools import m
from ..DI import DI
from ..plugin import Plugin


class BST(Plugin):
    name = 'Srstop'
    priority = 11
    
    def __init__(self):
        self.session = DI.session
        self.base_url = 'https://srstop.link'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
        self.session.headers = {"User-Agent": self.user_agent, "Referer": self.base_url}
        self.new_shows = urljoin(self.base_url, '/new-shows')
        self.all_shows = urljoin(self.base_url, '/browse-shows')
        self.imdb_rating = urljoin(self.base_url, '/tv-shows/imdb_rating')
        self.genres = urljoin(self.base_url, '/tv-shows')
        self.tv_tags = urljoin(self.base_url, '/tv-tags')
        self.show = urljoin(self.base_url, '/show')
        self.search_main = urljoin(self.base_url, '/search')
        self.search = urljoin(self.base_url, '/ajax/search.php?q=')
    

    def get_list(self, url: str) -> Optional[str]:
        if url == self.search_main:
            query = m.from_keyboard()
            if not query:
                sys.exit()
            return self.session.post(f'{self.search}{query}', timeout=10).json()
        elif self.all_shows in url:
            splitted = url.split('/')
            page_num = splitted[-1]
            if str.isdecimal(page_num):
                if page_num == 1:
                    return
                data = {
                    'genres': '["0"]',
                    'genreName': 'All Genres',
                    'years': '["0"]',
                    'sortby': 'date',
                    'p': str(page_num),
                    'ajax': '1'
                }
                response = self.session.post(url, data=data, timeout=10).text
                return response
    
    def parse_list(self, url: str, response: str) -> Optional[List[Dict[str, str]]]:
        if not url.startswith(self.base_url):
            return
        item_list = []
        if url == self.search_main:
            if not isinstance(response, list):
                m.ok('No results were found.')
                sys.exit()
            for item in response:
                title = item.get('title', '')
                link = item.get('permalink', '')
                thumbnail = item.get('image', '')
                item_list.append(
                    {
                        'type': 'dir',
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail,
                        'summary': title
                    }
                )
            return item_list
        soup = BeautifulSoup(response, 'html.parser')
        
        if url == self.genres:
            genres = soup.find_all(class_='cl-text')
            for genre in genres:
                item_list.append(
                    {
                        'type': 'dir',
                        'title': genre.a.text,
                        'link': f"{genre.a['href']}/1"
                    }
                )
            return item_list
        
        elif self.all_shows in url or url == self.imdb_rating or self.tv_tags in url:
            shows = soup.find_all('a', class_ = 'img_poster browse_now morph')
            for show in shows:
                title = show['title']
                link = show['href']
                thumbnail = re.compile("url\('(.+?)&amp").findall(str(show))[0]
                item_list.append(
                    {
                        'type': 'dir',
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail,
                        'summary': title
                    }
                )
            splitted = url.split('/')
            page_num = splitted[-1]
            if str.isdecimal(page_num):
                page_num = int(page_num) + 1
                link = f"{'/'.join(splitted[:-1])}/{page_num}"
                xbmc.log(f'link= {link}', xbmc.LOGINFO)
                item_list.append(
                    {
                        'type': 'dir',
                        'title': 'Next Page',
                        'link': link,
                        'summary': 'Next Page'
                    }
                )
            return item_list
        
        elif self.show in url:
            for ep in soup.find_all(class_='home-box'):
                name = ep.find_all(class_='episode')[1]
                title = f"{name['title']} {name.text}"
                link = ep.a['href']
                thumbnail = ep.a['data-original']
                item_list.append(
                    {
                        'type': 'item',
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail
                    }
                )
            if m.get_setting_bool('reverse.order') is False:
                item_list.reverse()
            return item_list
        
        titles = soup.find_all(class_ = 'hgrid')
        for title in titles:
            name = title.find(class_ = 'title tags').text
            ep_number = title.find('i').text
            ep_name = title.find('strong').text
            full_name = name + ' ' + ep_number.replace(' ','') + ' - "' + ep_name + '"'
            browse_now = title.find(class_ = 'browse_now morph')
            thumb = re.compile("url\('(.+?)&amp").findall(str(browse_now))[0]
            watch_now = title.find(class_ = 'watch_now morph')
            link = watch_now.get('href')
            fanart = re.compile("url\('(.+?)&amp").findall(str(watch_now))[0]
            item_list.append(
                {
                    'type': 'item',
                    'title': full_name,
                    'link': link, 
                    'thumbnail': thumb,
                    'fanart': fanart,
                    'summary': full_name
                }
            )
        pagination = soup.find(class_='spn-numbers')
        if pagination:
            pages = pagination.find_all('li')
            for page in pages:
                if "current" not in str(page):
                    item_list.append(
                        {
                            'type': 'dir',
                            'title': f'Page {page.a.text}',
                            'link': page.a.get('href', '')
                        }
                    )
        return item_list
    
    def play_video(self, item: Dict[str, str]) -> Optional[bool]:
        url = item.get('link', '')
        if not url.startswith(self.base_url):
            return 
        response = self.session.get(url, timeout=10).text
        soup = BeautifulSoup(response, 'html.parser')
        links_soup = soup.find_all(class_='embed-selector')
        links = []
        for link in links_soup:
            link_coded = re.compile("dbneg\('(.+?)'\)").findall(str(link))
            if not link_coded:
                m.ok('No Links Found')
                sys.exit()
            link_coded = link_coded[0]
            host = re.compile("domain=(.+?)'").findall(str(link))[0]
            url = self.dbneg_alt(link_coded)
            links.append([host, url])
        link = m.get_multilink(links)
        if link is False:
            sys.exit()
        title = item['title']
        thumbnail = item['thumbnail']
        try:
            import resolveurl
            if resolveurl.HostedMediaFile(link).valid_url():
                link = resolveurl.HostedMediaFile(link).resolve()
        except:
            pass
        if not isinstance(link, str):
            m.ok('The file cannot be played or has been removed.')
            sys.exit()
        liz = xbmcgui.ListItem(title, path=link)
        liz.setInfo('video', {'title': title, 'plot':title})
        liz.setArt({'thumb': thumbnail, 'icon': thumbnail, 'poster': thumbnail})
        xbmc.Player().play(link, listitem=liz)
        return True
    
    def dbneg_alt(self, s: str) -> str:
        # Credit to T4ils
        ret = ""
        offset = None
        split = s.split("-")
        for sp in split:
            code = int(sp, 16)
            if offset is None:
                offset = code - ord("h")
            char = chr(code - offset)
            ret += char
        return ret
    
    