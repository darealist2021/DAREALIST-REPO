from ..plugin import Plugin
from ..DI import DI


class http(Plugin):
    name = "http"
    priority = 0

    def get_list(self, url):
        if url.startswith("http"):
            return DI.session.get(url).text
