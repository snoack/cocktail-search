#!/usr/bin/env python3

import os
import re
import json
import mimetypes
import subprocess
import hashlib
from datetime import datetime
from functools import partial

import sphinxapi
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.routing import Map, Rule
from werkzeug.http import http_date

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


class CocktailsApp(object):
    urls = Map([
        Rule('/recipes', endpoint='recipes'),
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
        index_updated = datetime.fromtimestamp(int(os.stat(INDEX_FILE).st_mtime))
        if_modified_since = request.if_modified_since
        if if_modified_since is not None and if_modified_since >= index_updated:
            return Response(status=304)

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

        return Response(json.dumps(cocktails),
                        headers=[('Last-Modified', http_date(index_updated)),
                                 ('Cache-Control', 'no-cache')],
                        mimetype='application/json')

    def generate_css(self):
        args = ['lessc']
        args.extend(LESSC_OPTIONS)
        args.append(os.path.join(os.path.dirname(__file__), 'less', 'all.less'))

        with subprocess.Popen(args, stdout=subprocess.PIPE) as lessc:
            yield from lessc.stdout

    def render_template(self, filename, env):
        for data in env.get_template(filename).generate():
            yield data.encode('utf-8')

    def get_assets_checksum(self, env):
        if not hasattr(env, '_assets_checksum'):
            hash = hashlib.sha256()
            env._assets_checksum = ''

            def read(filename):
                with open(os.path.join(STATIC_FILES_DIR, filename), 'rb') as file:
                    return [file.read()]

            files = {f: partial(read, f) for f in os.listdir(STATIC_FILES_DIR)}
            for filename, func, volatile in self.get_generated_files(env):
                if volatile or filename not in files:
                    files[filename] = func

            for filename, func in sorted(files.items()):
                hash.update(filename.encode())
                for data in func():
                    hash.update(data)

            env._assets_checksum = hash.hexdigest()

        return env._assets_checksum

    def get_generated_files(self, env=None):
        yield 'all.css', self.generate_css, False

        if env is None:
            import jinja2

            directory = os.path.join(os.path.dirname(__file__), 'templates')
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(directory),
                                     autoescape=jinja2.select_autoescape())

            env.globals['site_url'] = SITE_URL
            env.globals['get_assets_checksum'] = partial(self.get_assets_checksum, env)

        for filename in env.loader.list_templates():
            yield filename, partial(self.render_template, filename, env), True

    def cmd_runserver(self, listen='8000'):
        from werkzeug.serving import run_simple

        def view_index(request):
            path = os.path.join(STATIC_FILES_DIR, 'index.html')
            return Response(open(path, 'rb'), mimetype='text/html')

        self.view_index = view_index
        self.urls.add(Rule('/', endpoint='index'))

        def view_generated(request, path):
            for filename, func, _ in self.get_generated_files():
                if path == filename:
                    mimetype = mimetypes.guess_type(path)[0]
                    return Response(func(), mimetype=mimetype)
            raise NotFound

        self.view_generated = view_generated
        self.urls.add(Rule('/static/<path:path>', endpoint='generated'))
        self.urls.add(Rule('/<any("serviceworker.js"):path>', endpoint='generated'))

        if ':' in listen:
            (address, port) = listen.rsplit(':', 1)
        else:
            (address, port) = ('localhost', listen)

        run_simple(address, int(port), app, use_reloader=True, static_files={
            '/static/': STATIC_FILES_DIR,
        })

    def cmd_deploy(self):
        for filename, func, _ in self.get_generated_files():
            print('Generating ' + filename)
            with open(os.path.join(STATIC_FILES_DIR, filename), 'wb') as outfile:
                for data in func():
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
