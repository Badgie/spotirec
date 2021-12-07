import re
import sys

from bs4 import BeautifulSoup

from spotirec.scrapers import ScraperBase


class ConcertScraper(ScraperBase.ScraperBase):
    """
    Scrapes concert data from the spotify.
    """
    def __init__(self, url: str, logger):
        """
        Checks if the url is a valid spotify concert url.
        """
        regex = r"[0-9a-zA-Z]{22}"
        if url.startswith('https://open.spotify.com/concert/') and re.match(regex + r"(/|)$", url):
            logger.debug('Matches on a full url')
        elif re.search('^' + regex + "$", url):
            logger.debug('Matches on an identifier')
            url = 'https://open.spotify.com/concert/' + url
        else:
            logger.error('The url you provided is not a valid spotify concert url or identifier of the concert')
            sys.exit(1)
        super().__init__(url, logger)

    def _run(self, soup) -> tuple[dict, str]:
        try:
            soup: BeautifulSoup
            concert_lineups = soup.find('section', class_='concert-section-container').find('div',
                                                                                            class_='wrapper').find_all('a')
            artist_ids = [concert_lineup.get('href').replace('/artist/', '') for concert_lineup in concert_lineups]
            artists = {x.find('div', class_='concert-artist-info-name').text.strip(): artist_ids[i] for i, x in
                       enumerate(concert_lineups)}
            concert_name = soup.find('h1').text.strip()
        except AttributeError:
            self.logger.error('It don\'t seem like there is anything on that url, could you please check again?')
            sys.exit(1)

        return artists, 'the concert ' + concert_name
