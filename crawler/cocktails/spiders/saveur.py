from urllib.parse import urljoin

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br, extract_extra_ingredients

xp_recipe_links = css_to_xpath('.SolrResultTitle a') + '/@href'
xp_next_link = css_to_xpath('.SolrPageNext a') + '/@href'

class SaveurSpider(BaseSpider):
	name = 'saveur'
	start_urls = ['http://www.saveur.com/solrSearchResults.jsp?fq=Course:Beverages']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select(xp_recipe_links).extract():
			yield Request(urljoin(response.url, url), self.parse_recipe)

		for url in hxs.select(xp_next_link).extract():
			yield Request(urljoin(response.url, url), self.parse)

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

		ingredients, extra_ingredients = extract_extra_ingredients(
			(
				split_at_br(hxs.select(
					"//node()"
						"[preceding::h4["
							"starts-with(text(),'INGREDIENTS') or "
							"starts-with(text(),'Ingredients') or "
							"starts-with(text(),'ingredients')"
						"]]"
						"[following::h4["
							"starts-with(text(),'INSTRUCTIONS') or "
							"starts-with(text(),'Instructions') or "
							"starts-with(text(),'instructions') or"
							"starts-with(text(),'DIRECTIONS') or "
							"starts-with(text(),'Directions') or "
							"starts-with(text(),'directions')"
						"]]"
				)) or
				hxs.select('//div[count(*)=1]/b').extract() or
				split_at_br(hxs.select('//b//node()')) or
				hxs.select("//span[@style='font-weight: bold;']").extract()
			),
			lambda s: s.isupper()
		)

		if not ingredients:
			return []

		return [CocktailItem(
			title=html_to_text(title).strip(),
			picture=picture,
			url=response.url,
			source='Saveur',
			ingredients=ingredients,
			extra_ingredients=extra_ingredients
		)]
