import re

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import CSSSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_title = CSSSelector('.recipe_title').path
xp_ingredients = CSSSelector('.ingredient').path


class DrinksMixerSpider(CrawlSpider):
    name = 'drinksmixer'
    allowed_domains = ['www.drinksmixer.com']
    start_urls = ['http://www.drinksmixer.com/']

    rules = (
        Rule(LinkExtractor(allow=r'/drink[^/]+.html$'), callback='parse_recipe'),
        Rule(LinkExtractor(allow=r'/cat/')),
    )

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        for title in hxs.select(xp_title).extract():
            break
        else:
            return []

        ingredients = hxs.select(xp_ingredients).extract()

        return [CocktailItem(
            title=re.sub(r'\s+recipe$', '', html_to_text(title)),
            picture=None,
            url=response.url,
            source='Drinks Mixer',
            ingredients=[html_to_text(x) for x in ingredients],
        )]
