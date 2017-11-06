from urllib.parse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import CSSSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

xp_title = CSSSelector('.entry-title').path
xp_ingredients = CSSSelector('.entry-content p').path + '[1]'
xp_previous_link = CSSSelector('.nav-previous a').path + '/@href'


class Monkey47Spider(BaseSpider):
    name = 'monkey47'
    start_urls = ['http://www.monkey47.com/wordpress/tag/gin_cocktail_rezepte/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(xp_title + '//a/@href').extract():
            yield Request(urljoin(response.url, url), self.parse_recipe)

        for url in hxs.select(xp_previous_link).extract():
            yield Request(urljoin(response.url, url), self.parse)

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        for title in hxs.select(xp_title).extract():
            break
        else:
            return []

        ingredients = []
        for ingredient in split_at_br(hxs.select(xp_ingredients)):
            if not ingredient.endswith(':'):
                ingredients.append(html_to_text(ingredient))

        return [CocktailItem(
            title=html_to_text(title).split(':')[-1].split('\u2013')[-1].strip(),
            picture=None,
            url=response.url,
            source='Monkey 47 Blog',
            ingredients=ingredients
        )]
