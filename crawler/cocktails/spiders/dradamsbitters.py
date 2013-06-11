import re
from urlparse import urljoin
from functools import partial

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, split_at_br

class DrAdamsBittersSpider(BaseSpider):
	name = 'dradamsbitters'
	start_urls = ['http://bokersbitters.co.uk/']

	def parse(self, response):
		hxs = HtmlXPathSelector(response)

		urls = hxs.select("//a[text() = 'Bitters']/following-sibling::ul//a/@href").extract()
		scraped_recipes = set()

		for url in urls:
			yield Request(urljoin(response.url, url), partial(
				self.parse_recipe,
				num_recipes=len(urls),
			 	scraped_recipes=scraped_recipes
			))

	def parse_recipe(self, response, num_recipes, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		ingredients = []
		for paragraph in hxs.select('//p'):
			l = []

			for line in split_at_br(paragraph, include_blank=True) + ['']:
				line = html_to_text(line).strip()

				if line:
					l.append(line)
					continue

				if len(l) >= len(ingredients):
					ingredients = l
					paragraph_with_ingredients = paragraph

				l = []

		title = hxs.select("//text()[contains(self::text(), ' such as the ')]")
		if title:
			title = html_to_text(title[0].extract())
			title = re.search(r'(?<= such as the ).+?(?=,|;| created )', title).group(0)
		else:
			title = paragraph_with_ingredients.select('./preceding-sibling::p')[-1]
			title = html_to_text(title.extract()).rstrip(';')

		yield CocktailItem(
			title=title,
			picture=None,
			url=response.url,
			source="Dr. Adam Elmegirab's",
			ingredients=ingredients
		)

		scraped_recipes.add(title.lower())
		if len(scraped_recipes) == num_recipes:
			yield Request(
				urljoin(
					response.url,
					hxs.select("//a[text() = 'Archives']/@href")[0].extract()
				),
				partial(
					self.parse_archive,
					scraped_recipes=scraped_recipes
				)
			)

	def parse_archive(self, response, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		for url in hxs.select("//a[contains(text(), 'Recipes')]/@href").extract():
			yield Request(urljoin(response.url, url), partial(
				self.parse_archive_recipes,
				scraped_recipes=scraped_recipes
			))

	def parse_archive_recipes(self, response, scraped_recipes):
		hxs = HtmlXPathSelector(response)

		for i, title_node in enumerate(hxs.select('//u[b][not(parent::div)] | //div[u[b]]')):
			title = html_to_text(title_node.extract()).strip().strip('.').title()
			if title.lower() in scraped_recipes:
				continue

			ingredients = []
			for line in split_at_br(title_node.select('./following-sibling::node()[not(preceding::u[b][%d])]' % (i + 2)), include_blank=True, newline_elements=['br', 'div', 'b']) + ['']:
				line = html_to_text(line).strip()

				if not line:
					if len(ingredients) == 1:
						ingredients = []
					if ingredients:
						break
					continue

				ingredients.append(line)

			if not ingredients:
				continue

			yield CocktailItem(
				title=title,
				picture=None,
				url=response.url,
				source="Dr. Adam Elmegirab's",
				ingredients=ingredients
			)
