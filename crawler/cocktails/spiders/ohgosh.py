from urllib.parse import urljoin, urlparse
from itertools import groupby
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_recipe_links = css_to_xpath('.cocktail') + '//a[1]/@href'


class OhGoshSpider(BaseSpider):
    name = 'ohgosh'
    start_urls = ['http://ohgo.sh/cocktail-recipes/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select(xp_recipe_links).extract()
        links = [urljoin(response.url, url) for url in links]
        links.sort()

        for page_url, recipe_urls in groupby(links, lambda url: url.split('#')[0]):
            yield Request(page_url, partial(
                self.parse_recipes,
                recipe_urls=list(recipe_urls)
            ))

    def parse_recipes(self, response, recipe_urls):
        hxs = HtmlXPathSelector(response)

        for url in recipe_urls:
            node = hxs.select("//*[@id='%s']" % urlparse(url).fragment)[0]

            for picture in node.select('./preceding-sibling::*[1]/img/@src').extract():
                picture = urljoin(url, picture)
                break
            else:
                picture = None

            ingredients = node.select('./following-sibling::*[position()<=2]/li').extract()

            yield CocktailItem(
                title=html_to_text(node.extract()),
                picture=picture,
                url=url,
                source='Oh Gosh!',
                ingredients=[html_to_text(x) for x in ingredients],
            )
