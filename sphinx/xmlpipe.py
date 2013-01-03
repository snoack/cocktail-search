#!/usr/bin/python

import sys
import os
import json
import re
from unicodedata import normalize
from itertools import imap, groupby
from difflib import SequenceMatcher

from werkzeug.utils import escape
from Stemmer import Stemmer

ee = lambda s: escape(s).encode('utf-8')
stemmer = Stemmer('english')

def normalize_title(s):
	s = re.sub(r'[^\w\s]', '', normalize('NFKD', s)).lower()
	s = ' '.join(stemmer.stemWords(s.split()))
	s = re.match('(?:the )?(.*?)(?: cocktail)?(?: for a crowd)?$', s).group(1)
	s = s.replace(' ', '')

	return s

def drop_duplicates(items):
	key = lambda item: normalize_title(item['title'])
	items = sorted(items, key=key)

	for title, items in groupby(items, key):
		yield max(items, key=lambda item: SequenceMatcher(None, title, item['url'].lower()).ratio())

def load_synonyms():
	synonyms = {}

	with open(os.path.join(os.path.dirname(__file__), 'synonyms.txt')) as f:
		for line in f:
			a, b = line.decode('utf-8').split('>')

			a = a.strip().lower()
			b = b.strip()

			synonyms.setdefault(a, []).append(b)

	return synonyms

def compile_synonyms():
	synonyms = load_synonyms()
	regex = re.compile(r'\b(?:%s)\b' % '|'.join(imap(re.escape, synonyms)), re.I)

	def expand(s):
		yield s

		for x in synonyms.get(s.lower(), []):
			for y in expand(x):
				yield y

	return (lambda s: regex.sub(lambda m : ' '.join(expand(m.group(0))), s))

expand_synonyms = compile_synonyms()

def xmlpipe():
	print '<?xml version="1.0" encoding="utf-8"?>'
	print '<sphinx:docset>'

	print '<sphinx:schema>'
	print '<sphinx:field name="title" attr="string"/>'
	print '<sphinx:field name="title_normalized" attr="string"/>'
	print '<sphinx:field name="ingredients"/>'
	print '<sphinx:attr name="url" type="string"/>'
	print '<sphinx:attr name="picture" type="string"/>'
	print '<sphinx:attr name="ingredients_text" type="string"/>'
	print '</sphinx:schema>'

	unique = False
	i = 1

	for arg in sys.argv[1:]:
		if arg == '-i':
			unique = False
			continue

		if arg == '-u':
			unique = True
			continue

		with open(arg) as file:
			items = imap(json.loads, file)

			if unique:
				items = drop_duplicates(items)

			for item in items:
				print '<sphinx:document id="%d">' % i
				print '<title>%s</title>' % ee(item['title'])
				print '<url>%s</url>' % ee(item['url'])

				if item['picture']:
					print '<picture>%s</picture>' % ee(item['picture'])

				print '<title_normalized>%s</title_normalized>' % ee(
					normalize_title(item['title'])
				)

				print '<ingredients>%s</ingredients>' % ee('!'.join(
					re.sub(r'[.!?\s]+', ' ', expand_synonyms(x))
						for y in (item['ingredients'], item.get('extra_ingredients', []))
						for x in y
				))

				print '<ingredients_text>%s</ingredients_text>' % ee('\n'.join(
					item['ingredients']
				))

				print '</sphinx:document>'

				i += 1

	print '</sphinx:docset>'

xmlpipe()
