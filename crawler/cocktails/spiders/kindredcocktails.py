from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import CSSSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = CSSSelector('.cocktail-ingredients tr').path


class KindredCocktails(CrawlSpider):
    name = 'kindredcocktails'
    allowed_domains = ['www.kindredcocktails.com']
    start_urls = ['http://www.kindredcocktails.com']

    rules = (
        Rule(LinkExtractor(allow=r'/cocktail/[^/?]+$'), callback='parse_recipe'),
        Rule(LinkExtractor(allow=r'.*')),
    )

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        for title in hxs.select('//h1').extract():
            break
        else:
            return []

        ingredients = hxs.select(xp_ingredients).extract()

        return [CocktailItem(
            title=html_to_text(title),
            picture=None,
            url=response.url,
            source='Kindred Cocktails',
            ingredients=[html_to_text(x) for x in ingredients],
        )]
