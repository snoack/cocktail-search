#!/usr/bin/python

import os
import re
import posixpath
import mimetypes
import subprocess
from collections import OrderedDict
import sphinxapi

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.utils import escape

try:
	import settings
except ImportError:
	settings = None

MAX_COCKTAILS_PER_PAGE = 20
MAX_RECIPES_PER_COCKTAIL = 10

SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000/')
SPHINX_HOST = getattr(settings, 'SPHINX_HOST', 'localhost')
SPHINX_PORT = getattr(settings, 'SPHINX_PORT', 9312)
LESSC_OPTIONS = getattr(settings, 'LESSC_OPTIONS', [])

STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), 'static')

RECIPE_TEMPLATE = '''\
<div class="recipe%(extra_css)s">
	<div class="picture">
		%(picture)s
	</div>
	<div class="details">
		<h2><a href="%(url)s">%(title)s</a></h2>
		<div class="ingredients-and-sources">
			<ul class="ingredients">
				%(ingredients)s
			</ul>
			<div class="sources">
				%(sources)s
			</div>
		</div>
	</div>
</div>'''

OPENSEARCH_TEMPLATE = '''\
<?xml version="1.0"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>Cocktail Search</ShortName>
    <Url type="text/html" template="%(site_url)s#{searchTerms}"/>
</OpenSearchDescription>
'''

class CocktailsApp(object):
	urls = Map([
		Rule('/recipes', endpoint='recipes'),
	])

	generated_files = {
		'css/styles.css': 'css',
		'opensearch.xml': 'open_search_description',
	}

	def make_query(self, sphinx, ingredients):
		queries = []

		for ingredient in ingredients:
			m = re.match(r'(\w+)\s*:\s*(\S.*)', ingredient)
			if m:
				field, ingredient = m.groups()
			else:
				field = 'ingredients'

			words = []
			for quoted, unquoted in re.findall(r'"(.*?)(?:"|$)|([^"]+)', ingredient):
				if quoted:
					words.extend(quoted)
				if unquoted:
					keywords = sphinx.BuildKeywords(unquoted.encode('utf-8'), 'recipes', 0)
					if keywords is None:
						return None
					for kw in keywords:
						words.append(kw['tokenized'])

			queries.append('@%s (%s)' % (
				field,
				' SENTENCE '.join(
					'"%s"' % sphinx.EscapeString(word) for word in words
				)
			))

		return ' | '.join(queries)

	def query(self, sphinx, ingredients, offset):
		query = self.make_query(sphinx, ingredients)
		if query is None:
			return None

		sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
		sphinx.SetRankingMode(sphinxapi.SPH_RANK_MATCHANY)
		sphinx.SetLimits(offset, MAX_COCKTAILS_PER_PAGE)
		sphinx.SetGroupBy('title_normalized', sphinxapi.SPH_GROUPBY_ATTR, '@relevance DESC, @count DESC, @id ASC')

		result = sphinx.Query(query)
		if not result:
			return None

		sphinx.SetLimits(0, MAX_RECIPES_PER_COCKTAIL)
		sphinx.ResetGroupBy()

		matches = result['matches']
		cocktails = []

		if matches:
			for match in matches:
				sphinx.AddQuery('(%s) & @title_normalized "^%s$"' % (
					query, sphinx.EscapeString(match['attrs']['title_normalized'])
				))

			results = sphinx.RunQueries()
			if not results:
				return None

			for result in results:
				if result['status'] == sphinxapi.SEARCHD_ERROR:
					return None

				cocktails.append(result['matches'])

		return cocktails

	def view_recipes(self, request):
		ingredients = [s for s in request.args.getlist('ingredient') if s.strip()]

		if not ingredients:
			return Response('', mimetype='text/html')

		try:
			offset = int(request.args['offset'])
		except (ValueError, KeyError):
			offset = 0

		sphinx = sphinxapi.SphinxClient()
		sphinx.SetServer(SPHINX_HOST, SPHINX_PORT)
		sphinx.Open()
		try:
			cocktails = self.query(sphinx, ingredients, offset)
		finally:
			sphinx.Close()

		output = []

		if cocktails is None:
			output.append('<div class="alert">')
			output.append(escape(sphinx.GetLastError()))
			output.append('</div>')
		else:
			for recipes in cocktails:
				output.append('<div class="cocktail">')

				sources = OrderedDict()
				for recipe in recipes:
					sources.setdefault(recipe['attrs']['source'], []).append(recipe)

				is_first = True
				for source, recipes in sources.iteritems():
					for recipe in recipes:
						attrs = recipe['attrs']

						output.append(RECIPE_TEMPLATE % {
							'title': escape(attrs['title']),
							'url': escape(attrs['url']),
							'picture': '<a href="%s"><img src="%s" alt="%s"/></a>' % (
								escape(attrs['url']),
								escape(attrs['picture']),
								escape(attrs['title']),
							) if attrs['picture'] else '<span></span>',
							'ingredients': ''.join(
								'<li>%s</li>' % escape(s) for s in attrs['ingredients_text'].splitlines()
							),
							'sources': '<h3>Source</h3><ul>%s</ul>' % ''.join(
								'<li>%s</li>' % ' '.join(
									'<a %s>%s</a>' % (
										'class="active"' if recipe is other_recipe else 'href="javascript:void(0)"',
										label
									) for other_recipe, label in zip(other_recipes, [
										other_source
									] + [
										'(%d)' % (i + 1) for i in xrange(1, len(other_recipes))
									])
								) for other_source, other_recipes in sources.iteritems()
							),
							'extra_css': ' active' if is_first else '',
						})

						is_first = False

				output.append('</div>')

		return Response(''.join(output), mimetype='text/html')

	def generate_css(self):
		lessc = subprocess.Popen([
			'lessc',
		] + LESSC_OPTIONS + [
			os.path.join(
				os.path.dirname(__file__),
				'styles.less'
			)
		], stdout=subprocess.PIPE)

		for line in lessc.stdout:
			yield line

		lessc.stdout.close()
		lessc.wait()

	def generate_open_search_description(self):
		return [OPENSEARCH_TEMPLATE % {'site_url': SITE_URL}]

	def cmd_runserver(self, listen='8000'):
		from werkzeug.serving import run_simple

		def view_index(request):
			path = os.path.join(STATIC_FILES_DIR, 'index.html')
			return Response(open(path, 'rb'), mimetype='text/html')

		self.view_index = view_index
		self.urls.add(Rule('/', endpoint='index'))

		def view_generated(request, path):
			endpoint = self.generated_files.get(path)
			if endpoint is None:
				raise NotFound
			iterable = getattr(self, 'generate_' + endpoint)()
			mimetype = mimetypes.guess_type(path)[0]
			return Response(iterable, mimetype=mimetype)

		self.view_generated = view_generated
		self.urls.add(Rule('/static/<path:path>', endpoint='generated'))

		if ':' in listen:
			(address, port) = listen.rsplit(':', 1)
		else:
			(address, port) = ('localhost', listen)

		run_simple(address, int(port), app, use_reloader=True, static_files={
			'/static/': STATIC_FILES_DIR,
		})

	def cmd_deploy(self):
		for path, endpoint in self.generated_files.iteritems():
			print 'Generating ' + path

			iterable = getattr(self, 'generate_' + endpoint)()
			path = os.path.join(STATIC_FILES_DIR, *posixpath.split(path))

			with open(path, 'wb') as outfile:
				for data in iterable:
					outfile.write(data)

	def dispatch_request(self, request):
		adapter = self.urls.bind_to_environ(request.environ)
		try:
			endpoint, values = adapter.match()
			return getattr(self, 'view_' + endpoint)(request, **values)
		except NotFound, e:
			return Response(status=404)
		except HTTPException, e:
			return e

	def call_command(self, command, args):
		getattr(self, 'cmd_' + command)(*args)

	def list_commands(self):
		return [x[4:] for x in dir(self) if x.startswith('cmd_')]

	def __call__(self, environ, start_response):
		return self.dispatch_request(Request(environ))(environ, start_response)

if __name__ == '__main__':
	import argparse

	app = CocktailsApp()

	parser = argparse.ArgumentParser()
	parser.add_argument('command', choices=app.list_commands())
	parser.add_argument('arg', nargs='*')
	args = parser.parse_args()

	app.call_command(args.command, args.arg)
