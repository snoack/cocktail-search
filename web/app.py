#!/usr/bin/python

import os
import re
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

SPHINX_HOST = getattr(settings, 'SPHINX_HOST', 'localhost')
SPHINX_PORT = getattr(settings, 'SPHINX_PORT', 9312)
LESSC_OPTIONS = getattr(settings, 'LESSC_OPTIONS', [])

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

class CocktailsApp(object):
	urls = Map([
		Rule('/recipes', endpoint='recipes'),
		Rule('/static/css/styles.css', endpoint='css'),
	])

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

	def on_recipes(self, request):
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

	def on_css(self, request):
		lessc = subprocess.Popen([
			'lessc',
		] + LESSC_OPTIONS + [
			os.path.join(
				os.path.dirname(__file__),
				'styles.less'
			)
		], stdout=subprocess.PIPE)

		response = Response(lessc.stdout, mimetype='text/css')
		response.call_on_close(lessc.wait)

		return response

	def dispatch_request(self, request):
		adapter = self.urls.bind_to_environ(request.environ)
		try:
			endpoint, values = adapter.match()
			return getattr(self, 'on_' + endpoint)(request, **values)
		except NotFound, e:
			return Response(status=404)
		except HTTPException, e:
			return e

	def __call__(self, environ, start_response):
		return self.dispatch_request(Request(environ))(environ, start_response)

if __name__ == '__main__':
	from werkzeug.wsgi import SharedDataMiddleware
	from werkzeug.serving import run_simple

	STATIC_FILES_DIR = os.path.join(os.path.dirname(__file__), 'static')

	def on_index(request):
		with open(os.path.join(STATIC_FILES_DIR, 'index.html')) as f:
			data = f.read()

		return Response(data, mimetype='text/html')

	app = CocktailsApp()
	app.on_index = on_index
	app.urls.add(Rule('/', endpoint='index'))
	app = SharedDataMiddleware(app, {'/static/': STATIC_FILES_DIR})

	run_simple('127.0.0.1', 5000, app)
