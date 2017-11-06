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

    git clone https://github.com/snoack/cocktail-search
    cd cocktail-search
    git submodule update --init


Installing dependencies
~~~~~~~~~~~~~~~~~~~~~~~

Following programs need to be installed:

* Python 2.7
* `Sphinx`_
* `Less`_
* `virtualenvwrapper`_ (optional)

On Debian/Ubuntu, you can install these with following command::

    apt-get install sphinxsearch node-less virtualenvwrapper

Assuming you use ``virtualenvwrapper`` (recommended for development), you can
create a virtualenv, and install the required Python modules in there, like that::

    mkvirtualenv -r requirements.txt cocktail-search
    wget https://raw.githubusercontent.com/sphinxsearch/sphinx/master/api/sphinxapi.py -O "$VIRTUAL_ENV/lib/python2.7/site-packages/sphinxapi.py"

Make sure that the virtualenv is active before you run ``scrapy``, ``indexer``
or ``app.py``. You can activate the virtual environment like that::

    workon cocktail-search


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

Anyway, following command will run the crawler for a given spider::

    cd crawler
    rm -f <spider>.json
    scrapy crawl <spider> -o <spider>.json

Note that when the output file already exist, Scrapy will append scraped recipes
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

Note that we omitted the ``--console`` option, in order to make searchd run in
the background. However instead of just calling searchd on the command line,
it would be even better to set up an init script to start and stop Sphinx.

There is rarely a need to restart the search daemon. When you have deployed a
new version or when you ran the crawler again, just rebuilt and rotate the index::

    cd sphinx
    indexer --all --rotate


Contributing
------------

This project is my playground for new web technologies and frameworks. And you
are invited to make it your playground as well. The code base is still small and
well organized. And setting up the development environment is fairly easy.

The easiest way to get started would probably be to write `spiders`_ for more
cocktail websites. Most spiders consists only of a few lines of Python code and
you don't have to know anything about the rest of the stack. Or you could
contribute to the `wordforms`_ and `synonyms`_ lists, even without any
programming skills. But you are also welcome to pick up any `open issue`_.
I prefer to get pull requests via GitHub, but will also accept patches via email.

You have found a bug and don't want to fix it yourself, or you have an awesome
idea to improve the cocktail search? That's great too. Please send me an email
or even better `submit an issue`_.

.. _demo: http://cocktails.etrigg.com/
.. _Sphinx: http://sphinxsearch.com/
.. _Less: http://lesscss.org/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/
.. _spiders: https://github.com/snoack/cocktail-search/tree/master/crawler/cocktails/spiders
.. _wordforms: https://github.com/snoack/cocktail-search/blob/master/sphinx/wordforms.txt
.. _synonyms: https://github.com/snoack/cocktail-search/blob/master/sphinx/synonyms.txt
.. _open issue: https://github.com/snoack/cocktail-search/issues?state=open
.. _submit an issue: https://github.com/snoack/cocktail-search/issues/new
