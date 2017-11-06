from urllib.parse import urljoin

from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector

from lxml.cssselect import css_to_xpath

from cocktails.items import CocktailItem
from cocktails.utils import html_to_text, unescape

xp_ingredient = css_to_xpath('.ingredient')


class EsquireSpider(SitemapSpider):
    name = 'esquire'
    sitemap_urls = ['http://www.esquire.com/robots.txt']
    sitemap_rules = [('/drinks/.*-recipe$', 'parse_recipe')]

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)

        for title in hxs.select("//meta[@property='og:title']/@content").extract():
            break
        else:
            return []

        for picture in hxs.select("//*[@id='drink_infopicvid']/img/@src").extract():
            picture = urljoin(response.url, picture)
            break
        else:
            picture = None

        ingredients = []
        for node in hxs.select("//ul[@id='ingredients']/li"):
            parts = []

            for child in node.select('* | text()'):
                text = html_to_text(child.extract())

                if 'ingredient' in (child.xmlNode.prop('class') or '').split():
                    text = text.split('--')[-1]

                text = text.strip()

                if not text:
                    continue

                parts.append(text)

            ingredients.append(' '.join(parts))

        # don't crawl recipes like 'American Whiskey & Canadian Whisky',
        # that only consist of pouring a single spirit into a glass.
        if len(ingredients) <= 1:
            return []

        return [CocktailItem(
            title=unescape(title),
            picture=picture,
            url=response.url,
            source='Esquire',
            ingredients=ingredients
        )]
