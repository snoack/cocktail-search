#!/usr/bin/python

import sys
import json
import re

from werkzeug.utils import escape

ee = lambda s: escape(s).encode('utf-8')

def xmlpipe():
	print '<?xml version="1.0" encoding="utf-8"?>'
	print '<sphinx:docset>'

	print '<sphinx:schema>'
	print '<sphinx:field name="title" attr="string"/>'
	print '<sphinx:attr name="url" type="string"/>'
	print '<sphinx:attr name="picture" type="string"/>'
	print '<sphinx:field name="ingredients"/>'
	print '<sphinx:attr name="ingredients_text" type="string"/>'
	print '</sphinx:schema>'

	i = 1

	for filename in sys.argv[1:]:
		with open(filename) as file:
			for line in file:
				doc = json.loads(line)

				print '<sphinx:document id="%d">' % i
				print '<title>%s</title>' % ee(doc['title'])
				print '<url>%s</url>' % ee(doc['url'])

				if doc['picture']:
					print '<picture>%s</picture>' % ee(doc['picture'])

				print '<ingredients>%s</ingredients>' % ee('!'.join(
					re.sub(r'[.!?\s]+', ' ', x)
						for y in (doc['ingredients'], doc.get('extra_ingredients', []))
						for x in y
				))

				print '<ingredients_text>%s</ingredients_text>' % ee('\n'.join(
					doc['ingredients']
				))

				print '</sphinx:document>'

				i += 1

	print '</sphinx:docset>'

xmlpipe()
