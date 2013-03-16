import re
from HTMLParser import HTMLParser

unescape = HTMLParser().unescape

def html_to_text(s):
	# strip tags
	s = re.sub(r'<[^>]*?>', '', s)
	# replace entities
	s = unescape(s)
	# replace all sequences of subsequent whitespaces with a single space
	s = re.sub(r'\s+', ' ', s)
	return s

def split_at_br(hxs):
	nodes = hxs.select('descendant-or-self::br|descendant-or-self::text()')
	snippets = []
	rv = []

	while True:
		node = nodes.pop(0) if nodes else None

		if node and node.xmlNode.name != 'br':
			snippets.append(node.extract())
			continue

		s = ''.join(snippets).strip()
		snippets = []

		if s:
			rv.append(s)

		if not node:
			return rv
