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

PAGE_SIZE = 20

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

	def on_recipes(self, request):
		ingredients = [s for s in request.args.getlist('ingredient') if s.strip()]

		if not ingredients:
			return Response('', mimetype='text/html')

		sphinx = sphinxapi.SphinxClient()
		query = '@ingredients ' + ' | '.join(
			'(%s)' % ' SENTENCE '.join(
				'"%s"' % sphinx.EscapeString(word)
					for x in re.findall(r'"(.*?)(?:"|$)|(\S+)', s)
					for word in x if word
			) for s in ingredients
		)

		try:
			offset = int(request.args['offset'])
		except (ValueError, KeyError):
			offset = 0

		sphinx.SetServer(SPHINX_HOST, SPHINX_PORT)
		sphinx.SetMatchMode(sphinxapi.SPH_MATCH_EXTENDED2)
		sphinx.SetLimits(offset, PAGE_SIZE)

		sphinx.Open()
		try:
			result = sphinx.Query(query)
		finally:
			sphinx.Close()

		if result:
			output = '\n'.join(
				RECIPE_TEMPLATE % {
					'title': escape(m['attrs']['title']),
					'url': escape(m['attrs']['url']),
					'picture': '<a href="%s"><img src="%s" alt="%s"/></a>' % (
						escape(m['attrs']['url']),
						escape(m['attrs']['picture']),
						escape(m['attrs']['title']),
					) if m['attrs']['picture'] else '&nbsp;',
					'ingredients': ''.join(
						'<li>%s</li>' % escape(s) for s in m['attrs']['ingredients_text'].splitlines()
					),
				} for m in result['matches']
			)
		else:
			output = '<div class="alert">%s</div>' % escape(sphinx.GetLastError())

		return Response(output, mimetype='text/html')

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
