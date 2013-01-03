from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

xp_ingredients = css_to_xpath('.recipeMeasure')

class CocktailDbSpider(CrawlSpider):
	name = 'cocktaildb'
	allowed_domains = ['www.cocktaildb.com']
	start_urls = ['http://www.cocktaildb.com']

	rules = (
		Rule(SgmlLinkExtractor(allow=r'/recipe_detail\b'), callback='parse_recipe'),
		Rule(SgmlLinkExtractor(allow=r'.*')),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select('//h2').extract():
			break
		else:
			return []

		ingredients = hxs.select(xp_ingredients).extract()

		return [CocktailItem(
			title=html_to_text(title),
			picture=None,
			url=response.url,
			ingredients=map(html_to_text, ingredients),
		)]
