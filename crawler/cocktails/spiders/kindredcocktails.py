from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = css_to_xpath('.cocktail-ingredients tr')

class KindredCocktails(CrawlSpider):
    name = 'kindredcocktails'
    allowed_domains = ['www.kindredcocktails.com']
    start_urls = ['http://www.kindredcocktails.com']

    rules = (
        Rule(SgmlLinkExtractor(allow=r'/cocktail/[^/?]+$'), callback='parse_recipe'),
        Rule(SgmlLinkExtractor(allow=r'.*')),
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
