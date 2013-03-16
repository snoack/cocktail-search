from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

xp_title = css_to_xpath('.entry-title')
xp_ingredients = css_to_xpath('.entry-content p') + '[1]'
xp_previous_link = css_to_xpath('.nav-previous a') + '/@href'

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
			title=html_to_text(title).split(':')[-1].split(u'\u2013')[-1].strip(),
			picture=None,
			url=response.url,
			ingredients=ingredients
		)]
