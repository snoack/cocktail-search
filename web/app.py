#!/usr/bin/env python3

import os
import re
import json
import posixpath
import mimetypes
import subprocess
from urllib.parse import urlencode

import sphinxapi
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.routing import Map, Rule
from werkzeug.urls import url_decode

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
INDEX_FILE = os.path.join(os.path.dirname(__file__), os.path.pardir, 'sphinx', 'idx_recipes.spd')

OPENSEARCH_TEMPLATE = '''\
<?xml version="1.0"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>Cocktail Search</ShortName>
    <Url type="text/html" template="%(site_url)s#{searchTerms}"/>
</OpenSearchDescription>
'''

JSLICENSE_TEMPLATE = '''\
<!DOCTYPE html>
<html>
<head>
<title>Cocktail search | JavaScript License Information</title>
</head>
<body>
<table id="jslicense-labels1">
<tr>
<td><a href="http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js">jquery.min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jquery/jquery/archive/1.9.1.zip">jquery-1.9.1.zip</a></td>
</tr>
<tr>
<td><a href="http://cdnjs.cloudflare.com/ajax/libs/underscore.js/1.4.4/underscore-min.js">underscore-min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jashkenas/underscore/archive/1.4.4.zip">underscore-1.4.4.zip</a></td>
</tr>
<tr>
<td><a href="http://cdnjs.cloudflare.com/ajax/libs/backbone.js/1.0.0/backbone-min.js">backbone-min.js</a></td>
<td><a href="http://www.jclark.com/xml/copying.txt">Expat</a></td>
<td><a href="https://github.com/jashkenas/backbone/archive/1.0.0.zip">backbone-1.0.0.zip</a></td>
</tr>
<tr>
<td><a href="%(site_url)sstatic/script.js">script.js</a></td>
<td><a href="http://www.gnu.org/licenses/agpl-3.0.html">GNU-AGPL-3.0</a></td>
<td><a href="%(site_url)sstatic/script.js">script.js</a></td>
</tr>
</table>
</body>
</html>
'''


class CocktailsApp(object):
    urls = Map([
        Rule('/recipes', endpoint='recipes'),
    ])

    generated_files = {
        'all.css': 'css',
        'opensearch.xml': 'open_search_description',
        'jslicense.html': 'jslicense',
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
                    keywords = sphinx.BuildKeywords(unquoted, 'recipes', 0)
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
        index_updated = int(os.stat(INDEX_FILE).st_mtime)
        if request.args.get('index_updated') != str(index_updated):
            return Response(status=302, headers={
                'Location': '/recipes?' + urlencode(
                    [('index_updated', index_updated)] +
                    [(k, v) for k, v
                        in url_decode(request.query_string, cls=iter)
                        if k != 'index_updated'],
                    doseq=True
                ),
            })

        ingredients = [s for s in request.args.getlist('ingredient') if s.strip()]
        cocktails = []
        if ingredients:
            try:
                offset = int(request.args['offset'])
            except (ValueError, KeyError):
                offset = 0

            sphinx = sphinxapi.SphinxClient()
            sphinx.SetServer(SPHINX_HOST, SPHINX_PORT)
            sphinx.Open()
            try:
                result = self.query(sphinx, ingredients, offset)
            finally:
                sphinx.Close()

            if result is None:
                raise InternalServerError(sphinx.GetLastError())

            for group in result:
                recipes = []
                for match in group:
                    recipes.append({
                        'title':       match['attrs']['title'],
                        'ingredients': match['attrs']['ingredients_text'].splitlines(),
                        'url':         match['attrs']['url'],
                        'picture_url': match['attrs']['picture'],
                        'source':      match['attrs']['source'],
                    })
                cocktails.append({'recipes': recipes})

        return Response(
            json.dumps({
                'cocktails': cocktails,
                'index_updated': index_updated,
            }),
            headers={'Cache-Control': 'public, max-age=31536000'},
            mimetype='application/json'
        )

    def generate_css(self):
        args = ['lessc']
        args.extend(LESSC_OPTIONS)
        args.append(os.path.join(os.path.dirname(__file__), 'less', 'all.less'))

        with subprocess.Popen(args, stdout=subprocess.PIPE) as lessc:
            yield from lessc.stdout

    def generate_open_search_description(self):
        return [OPENSEARCH_TEMPLATE % {'site_url': SITE_URL}]

    def generate_jslicense(self):
        return [JSLICENSE_TEMPLATE % {'site_url': SITE_URL}]

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
        for path, endpoint in self.generated_files.items():
            print('Generating ' + path)

            iterable = getattr(self, 'generate_' + endpoint)()
            path = os.path.join(STATIC_FILES_DIR, *posixpath.split(path))

            with open(path, 'wb') as outfile:
                for data in iterable:
                    if isinstance(data, str):
                        data = data.encode('utf-8')
                    outfile.write(data)

    def dispatch_request(self, request):
        adapter = self.urls.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'view_' + endpoint)(request, **values)
        except NotFound as e:
            return Response(status=404)
        except HTTPException as e:
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
