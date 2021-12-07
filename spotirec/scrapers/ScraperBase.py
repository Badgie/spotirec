import pathlib
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup


class ScraperBase(ABC):
    """
    Abstract class for scraping any page.
    An inherited class should implement _run
    """
    url: str = ""

    def __init__(self, url, logger, is_file=False):
        self.url = url
        self.logger = logger
        self.is_file = is_file

    def run(self) -> dict:
        if self.is_file:
            return self._run(BeautifulSoup(open(self.url), "html.parser"))
        return self._run(BeautifulSoup(
            requests.get(self.url).text,
            'html.parser'))

    @abstractmethod
    def _run(self, soup: BeautifulSoup) -> dict:
        raise NotImplemented("This should be implemented")
