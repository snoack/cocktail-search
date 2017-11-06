from urllib.parse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_recipes = css_to_xpath('.hrecipe')
xp_ingredients = css_to_xpath('.ingredient li')


class WikipediaSpider(CrawlSpider):
    name = 'wikipedia'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['http://en.wikipedia.org/wiki/List_of_cocktails']

    rules = (
        Rule(SgmlLinkExtractor(allow=(r'/wiki/Category:Cocktails(\b|_)'))),
        Rule(SgmlLinkExtractor(allow=(r'/wiki/Category:.+(\b|_)drinks?(\b|_)'))),
        Rule(SgmlLinkExtractor(allow=(r'/wiki/[^:]+$')), callback='parse_recipes'),
    )

    def parse_recipes(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select("//link[@rel='canonical']/@href").extract():
            url = urljoin(response.url, url)

            if url != response.url:
                yield Request(url, callback=self.parse_recipes)
                raise StopIteration

        for recipe in hxs.select(xp_recipes):
            for title in recipe.select('caption').extract():
                break
            else:
                continue

            ingredients = recipe.select(xp_ingredients).extract()
            if not ingredients:
                continue

            for picture in recipe.select("tr/td[@colspan='2']//img/@src | preceding-sibling::*[contains(concat(' ', normalize-space(@class), ' '), ' thumb ')]//img/@src").extract():
                picture = urljoin(response.url, picture)
                break
            else:
                picture = None

            yield CocktailItem(
                title=html_to_text(title),
                picture=picture,
                url=response.url,
                source='Wikipedia',
                ingredients=[html_to_text(x) for x in ingredients]
            )
