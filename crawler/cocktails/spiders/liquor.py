from urlparse import urljoin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text

class LiqourSpider(CrawlSpider):
	name = 'liquor'
	allowed_domains = ['liquor.com']
	start_urls = ['http://liquor.com/recipes/']

	rules = (
		Rule(SgmlLinkExtractor(allow=(r'/recipes/page/',))),
		Rule(SgmlLinkExtractor(allow=(r'/recipes/.+')), callback='parse_recipe'),
	)

	def parse_recipe(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select('//h1').extract():
			break
		else:
			return []

		for picture in hxs.select("//img[@itemprop='photo']/@src").extract():
			picture = urljoin(response.url, picture)
			break
		else:
			picture = None

		ingredients = hxs.select("//*[@itemprop='ingredient']").extract()

		return [CocktailItem(
			title=html_to_text(title),
			picture=picture,
			url=response.url,
			ingredients=map(html_to_text, ingredients),
		)]
