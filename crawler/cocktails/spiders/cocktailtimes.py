from urllib.parse import urljoin

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import CSSSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_header = CSSSelector('.header').path + '/text()'
xp_ingredients = CSSSelector('.story').path + ("[1]//text()["
    "preceding::text()["
        "normalize-space(self::text()) = 'Ingredients:'"
    "]"
"]["
    "starts-with(normalize-space(self::text()), '-')"
"]")
xp_picture = ("//img["
    "preceding::comment()["
        "contains(self::comment(), ' COCKTAIL PHOTO ')"
    "]"
"]/@src")


class CocktailTimesSpider(CrawlSpider):
    name = 'cocktailtimes'
    allowed_domains = ['www.cocktailtimes.com']
    start_urls = ['http://www.cocktailtimes.com']

    rules = (
        Rule(
            LinkExtractor(
                allow=(
                    r'/whiskey/.+',
                    r'/bourbon/.+',
                    r'/scotch/.+',
                    r'/vodka/.+',
                    r'/gin/.+',
                    r'/rum/.+',
                    r'/tequila/.+',
                    r'/brandy/.+',
                    r'/hot/.+',
                    r'/blend/.+',
                    r'/tropical/.+',
                    r'/shooter/.+',
                    r'/original/.+')
            ),
            callback='parse_recipe',
            follow=True
        ),
        Rule(LinkExtractor(allow=r'.*')),
    )

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        ingredients = [html_to_text(s).split('-', 1)[1].strip() for s in hxs.select(xp_ingredients).extract()]
        if not ingredients:
            return []

        for title in hxs.select(xp_header).extract():
            break
        else:
            return []

        for picture in hxs.select(xp_picture).extract():
            picture = urljoin(response.url, picture)
        else:
            picture = None

        return [CocktailItem(
            title=html_to_text(title),
            picture=picture,
            url=response.url,
            source='Cocktail Times',
            ingredients=ingredients,
        )]
