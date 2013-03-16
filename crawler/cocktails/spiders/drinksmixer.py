import re

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_title = css_to_xpath('.recipe_title')
xp_ingredients = css_to_xpath('.ingredient')

class DrinksMixerSpider(CrawlSpider):
	name = 'drinksmixer'
	allowed_domains = ['www.drinksmixer.com']
	start_urls = ['http://www.drinksmixer.com/']

	rules = (
		Rule(SgmlLinkExtractor(allow=r'/drink[^/]+.html$'), callback='parse_recipe'),
		Rule(SgmlLinkExtractor(allow=r'/cat/')),
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
			ingredients=map(html_to_text, ingredients),
		)]
