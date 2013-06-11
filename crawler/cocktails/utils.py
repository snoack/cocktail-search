import re
from HTMLParser import HTMLParser
from collections import OrderedDict

from scrapy.selector import XPathSelector

unescape = HTMLParser().unescape

def html_to_text(s):
	# strip tags
	s = re.sub(r'<[^>]*?>', '', s)
	# replace entities
	s = unescape(s)
	# replace all sequences of subsequent whitespaces with a single space
	s = re.sub(r'\s+', ' ', s)
	return s

def split_at_br(hxs, include_blank=False, newline_elements=['br']):
	nodes = hxs.select('|'.join('descendant-or-self::' + el for el in newline_elements + ['text()']))
	snippets = []
	rv = []

	while True:
		node = nodes.pop(0) if nodes else None

		if node and node.xmlNode.name not in newline_elements:
			snippets.append(node.extract())
			continue

		s = ''.join(snippets).strip()
		snippets = []

		if s or include_blank:
			rv.append(s)

		if not node:
			return rv

def extract_extra_ingredients(nodes, is_section_header):
	section = None
	sections = OrderedDict()

	for node in nodes:
		text = node.extract() if isinstance(node, XPathSelector) else node
		text = html_to_text(text).strip()

		if not text:
			continue

		if is_section_header(node):
			section = text
			continue

		sections.setdefault(section, []).append(text)

	if None in sections:
		ingredients = sections.pop(None)
	elif sections:
		ingredients = sections.pop(sections.keys()[-1])
	else:
		ingredients = []

	extra_ingredients = [x for y in sections.values() for x in y]

	return (ingredients, extra_ingredients)
