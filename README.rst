Cocktail search
===============

Simple but powerful open source web application and crawler for searching
cocktail recipes from the web. Check out the `demo`_ or read below to run
it on your own machine. 


Getting started
---------------

Cloning the repository
~~~~~~~~~~~~~~~~~~~~~~

If you are going to create the virtual environment (see next section), then
create a directory which becomes the parent directory of the repository and
will be otherwise empty::

    mkdir cocktail-search
    cd cocktail-search

Clone the repository and its submodules::

    git clone https://github.com/wallunit/cocktail-search
    cd cocktail-search
    git submodule init
    git submodule update


Installing dependencies
~~~~~~~~~~~~~~~~~~~~~~~

There is a script that creates a `virtual environment`_ and installs all
dependencies into the environment. Assuming you have virtualenv and pip already
installed and that you have created the directory, that became the parent
directory of the repository, as described in the previous section, run following
command::

    ./bootstrap-virtualenv.sh ..

If it still fails, it is most likely because of you are missing a development
package required to build one of the dependencies. In that case install the
missing package and start over.

Make sure that the virtual environment is active before you run scrapy, searchd,
indexer or app.py. You can activate the virtual environment like that::

    source ../bin/activate

Alternatively you can install the dependencies system-wide. For the Python
packages have a look at *requirements.txt* or just run ``pip install -r requirements.txt``.
For the other dependencies have a look at the contents of *bootstrap-virtualenv.sh*.


Crawling
~~~~~~~~

Crawling websites will consume not only a lot of your bandwidth, but generates
also a lot of traffic on the websites you are crawling. So please be nice and
don't run the crawler unless absolutely necessary, for example when you have to
test a spider, that you have just added or modified. For any other case, I made
the files with the cocktail recipes I have already crawled available for you::

    wget -r -A .json http://cocktails.etrigg.com/dumps/
    mv cocktails.etrigg.com/dumps/* crawler/
    rm -r cocktails.etrigg.com

However following command will run the crawler for a given spider::

    cd crawler
    rm -f <spider>.json
    scrapy crawl <spider> -o <spider>.json

Note that when the output file already exist, scrapy will append scraped recipes
at the bottom of the existing file. So make sure you delete it before.


Setting up Sphinx
~~~~~~~~~~~~~~~~~

There is no RDBMS. All data are stored in a Sphinx index that is built from the
crawled cocktail recipes. In order to built the index and run the search daemon
in the console, just run::

    cd sphinx
    indexer --all
    searchd --console


Running the development server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to serve the website from your local machine and start hacking, there
is no need to setup an advanced web server like Apache. Just run the development
server and go to http://localhost:8000/ with your web browser::

    ./web/app.py runserver

By default the development server only listens on localhost. However if you want
to access the website from an other device you can make it also listen on all
interfaces::

    ./web/app.py runserver 0.0.0.0:8000


Deploying the production environment
------------------------------------

Configuring the web app
~~~~~~~~~~~~~~~~~~~~~~~

Create the file *web/settings.py* and set follwing options::

    SITE_URL = 'http://cocktails.etrigg.com/'
    LESSC_OPTIONS = ['--compress']


Configuring Apache
~~~~~~~~~~~~~~~~~~

::

        <VirtualHost *:80>
                ServerName cocktails.etrigg.com

                WSGIDaemonProcess cocktails [processes=<num>] [python-path=<path to environment>/lib/python2.7/site-packages]
                WSGIProcessGroup  cocktails
                WSGIScriptAlias   / <path to repository>/web/app.wsgi

                Alias /static <path to repository>/web/static

                RewriteEngine On
                RewriteRule ^/$ /static/index.html [P]
        </VirtualHost>

The ``processes`` option is required to utilize multiple CPU units or cores, in order
to handle concurrent requests faster.

The ``python-path`` option is required when you have used virtualenv to install the
dependencies.


Generating static files
~~~~~~~~~~~~~~~~~~~~~~~

Some static files (like the CSS which is compiled from less) are generated on
the fly in the development environment, but must be compiled when deploying the
production environment, in order to serve them faster::

    ./web/app.py deploy

Remember to call that command every time you deploy a new version.


Setting up Sphinx
~~~~~~~~~~~~~~~~~

Build the index and start the search daemon::

    cd sphinx
    indexer --all
    searchd

Note that we omitted the ``--console`` option, in order to make searchd run in the
background. However instead of just calling searchd on the command line, it
would be even better to set up an init script to start and stop Sphinx.

There is rarely a need to restart the search daemon. When you have deployed a
new version of the cocktail search or when you ran the crawler again, just
rebuilt and rotate the index::

    cd sphinx
    indexer --all --rotate


Getting involved
----------------

This project is my playground for new web technologies and frameworks. And you
are invited to make it your playground as well. The code base is still small and
well organized. And setting up the development environment is easy and
straightforward. 

The easiest way to get involved would probably be to write `spiders`_ for more
cocktail websites. Most spiders consists only of a few lines of Python code and
you don't have to know anything about the rest of the stack. Or you could
contribute to the `wordforms`_ and `synonyms`_ lists, without even any
programming skills. Also have a look at the `open issues`_ and feel free to fix
some of them. I prefer to get pull requests via github, but will also accept
patches via email.

You have found a bug and don't want to fix it yourself. Or you have an awesome
idea to improve the cocktail search? That's great. Please send me an email or
even better `use the issue tracker`_.

.. _demo: http://cocktails.etrigg.com/
.. _virtual environment: http://www.virtualenv.org/
.. _werkzeug: http://www.pocoo.org/projects/werkzeug/
.. _scrapy: http://scrapy.org/
.. _Sphinx: http://sphinxsearch.com/
.. _less: http://lesscss.org/
.. _install node.js: https://github.com/joyent/node/wiki/Installing-Node.js-via-package-manager
.. _spiders: https://github.com/wallunit/cocktail-search/tree/master/crawler/cocktails/spiders
.. _wordforms: https://github.com/wallunit/cocktail-search/blob/master/sphinx/wordforms.txt
.. _synonyms: https://github.com/wallunit/cocktail-search/blob/master/sphinx/synonyms.txt
.. _open issues: https://github.com/wallunit/cocktail-search/issues?state=open
.. _use the issue tracker: https://github.com/wallunit/cocktail-search/issues/new
