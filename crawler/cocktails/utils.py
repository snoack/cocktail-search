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
