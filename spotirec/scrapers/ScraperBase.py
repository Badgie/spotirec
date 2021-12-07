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

    def __init__(self, url, logger):
        self.url = url
        self.logger = logger

    def run(self) -> dict:
        return self._run(BeautifulSoup(
            requests.get(self.url).text,
            'html.parser'))

    @abstractmethod
    def _run(self, soup: BeautifulSoup) -> dict:
        raise NotImplemented("This should be implemented")
