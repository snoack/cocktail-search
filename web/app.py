#!/usr/bin/python

import re
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

RECIPE_TEMPLATE = '''\
<div class="recipe">
	<div class="picture">
		%(picture)s
	</div>
	<div class="details">
		<h2><a href="%(url)s">%(title)s</a></h2>
		<ul>
			%(ingredients)s
		</ul>
	</div>
</div>'''

class CocktailsApp(object):
	urls = Map([
		Rule('/recipes', endpoint='recipes'),
	])

	def query(self, sphinx, ingredients, offset):
		query = '@ingredients ' + ' | '.join(
			'(%s)' % ' SENTENCE '.join(
				'"%s"' % sphinx.EscapeString(word)
					for quoted, unquoted in re.findall(r'"(.*?)(?:"|$)|([^"]+)', s)
					for word in (quoted and [quoted] or [
						kw['tokenized'] for kw in sphinx.BuildKeywords(
							unquoted.encode('utf-8'), 'recipes', 0
						)
					])
			) for s in ingredients
		)

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
				output.append('<ul class="nav nav-pills">')

				for recipe in recipes:
					output.append('<li><a href="')
					output.append(escape(recipe['attrs']['url']))
					output.append('"><span></span></a></li>')

				output.append('</ul>')

				for recipe in recipes:
					attrs = recipe['attrs']

					output.append(RECIPE_TEMPLATE % {
						'title': escape(attrs['title']),
						'url': escape(attrs['url']),
						'picture': '<a href="%s"><img src="%s" alt="%s"/></a>' % (
							escape(attrs['url']),
							escape(attrs['picture']),
							escape(attrs['title']),
						) if attrs['picture'] else '&nbsp;',
						'ingredients': ''.join(
							'<li>%s</li>' % escape(s) for s in attrs['ingredients_text'].splitlines()
						),
					})

				output.append('</div>')

		return Response(''.join(output), mimetype='text/html')

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
	import os

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
