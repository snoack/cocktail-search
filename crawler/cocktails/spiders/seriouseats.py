import json
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import extract_extra_ingredients

URL = 'http://www.seriouseats.com/topics/search?index=recipe&count=200&term=c|cocktails'

xp_ingredients = css_to_xpath('.ingredient')

class SeriouseatsSpider(BaseSpider):
	name = 'seriouseats'
	start_urls = [URL]

	def parse(self, response):
		recipes = json.loads(response.body)['entries']

		for recipe in recipes:
			picture = None

			for size in sorted(int(k[10:]) for k in recipe if k.startswith('thumbnail_')):
				picture = recipe['thumbnail_%d' % size]

				if picture:
					if 'strainerprimary' not in picture and 'cocktailChroniclesBug' not in picture:
						break

					picture = None
				
			yield Request(recipe['permalink'], partial(
				self.parse_recipe,
				title=recipe['title'].split(':')[-1].strip(),
				picture=picture
			))

		if recipes:
			yield Request('%s&before=%s' % (URL, recipe['id']), self.parse)

	def parse_recipe(self, response, title, picture):
		hxs = HtmlXPathSelector(response)

		ingredients, extra_ingredients = extract_extra_ingredients(
			hxs.select(xp_ingredients),
			lambda node: node.select('strong')
		)

		yield CocktailItem(
			title=title,
			picture=picture,
			url=response.url,
			source='Serious Eats',
			ingredients=ingredients,
			extra_ingredients=extra_ingredients
		)
