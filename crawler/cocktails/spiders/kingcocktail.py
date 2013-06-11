import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

class kingCocktailSpider(BaseSpider):
	name = 'kingcocktail'
	start_urls = [
		'http://www.kingcocktail.com/bitters-recipes.html',
		'http://www.kingcocktail.com/bitters-recipes2.html',
	]

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		for title in hxs.select("//strong[normalize-space(text()) != '']"):
			lines = split_at_br(title.select("ancestor-or-self::node()/following-sibling::node()[not(self::span[starts-with(text(), 'Stir')])]"), include_blank=True)
			ingredients = []

			for line in lines[1 + (not lines[1][:1].isdigit()):]:
				line = html_to_text(line).strip()

				if not line:
					break

				if re.search(r'\b(?:shaken?|stir(?:red)?|fill glass|preparation)\b', line, re.I):
					break

				ingredients.append(line)

			yield CocktailItem(
				title=html_to_text(title.extract()).strip().rstrip('*').title(),
				picture=None,
				url=response.url,
				source="Dale DeGroff's",
				ingredients=ingredients
			)
