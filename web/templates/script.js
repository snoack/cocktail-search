var waitingForServiceWorker = false;
var collection = null;

if ('serviceWorker' in navigator && 'caches' in window) {
  // Defer queries until the Service Worker is controlling this client,
  // to make sure that the initial query is cached. Otherwise, when going
  // offline, reloading the page won't show any data.
  waitingForServiceWorker = true;
  navigator.serviceWorker.register('/serviceworker.js').then(
    function(registration) {
      // If the Service Worker is active right after registration, that means it
      // was already installed before, and if it is not controlling this client
      // yet, it likely never will during this session. This happens for example
      // when force reloading (Ctrl+F5) or when there is another active client
      // still being controlled by an outdated version of the Service Worker.
      if (!registration.active)
        return new Promise(function(resolve) {
          navigator.serviceWorker.addEventListener('controllerchange', resolve)
        });
    },
    // If registration fails, log the error, but don't propagate
    // the error down the Promise chain, so that we stop waiting,
    // still performing any query (but without caching).
    console.error
  ).then(function() {
    waitingForServiceWorker = false;
    if (collection)
      collection.retry();
  });

  // Populate the cache with our assets, based on the resources that have been
  // encountered during page load. Normally, you'd hard-code your assets inside
  // the Service Worker and have it add them to the cache during installation.
  // However, we don't want to block installation, to not slow down first load,
  // as we wait for the Service Worker (see above). Then again, if the Service
  // Worker being installed doesn't imply all assets being cached, we have to
  // keep try fetching missing assets. Furthermore, the location of some of our
  // assets (i.e. the Google Web Font) cannot be predicted in advance.
  window.addEventListener('load', function() {
    caches.open('assets:{{ get_assets_checksum() }}').then(function(cache) {
      var assets = [document.location.href];
      var entries = performance.getEntriesByType('resource');

      for (var i = 0; i < entries.length; i++) {
        var entry = entries[i];
        var type = entry.initiatorType;
        if (type == 'link' || type == 'script' || type == 'css')
          assets.push(entry.name);
      }

      assets.forEach(function(url) {
         cache.match(url).then(function(response) {
          if (!response)
            cache.add(url);
        });
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", function() {
  var Cocktail = Backbone.Model.extend();

  var SearchResults = Backbone.Collection.extend({
    model: Cocktail,

    url: function() {
      return '/recipes' + (this.ingredients.length == 0 ? '' : '?' + $.param(
        this.ingredients.map(function(ingredient) {
          return {name: 'ingredient', value: ingredient};
        })
      ));
    },

    parse: function(resp, options) {
      this.canLoadMore = resp.length > 0;
      return resp;
    },

    query: function(ingredients) {
      this.ingredients = ingredients;
      this.isStale = waitingForServiceWorker;

      if (!waitingForServiceWorker)
        this.fetch({error: function(collection) {
          collection.isStale = true;
          collection.set([]);
        }});
    },

    retry: function() {
      if (this.isStale)
        this.query(this.ingredients);
    }
  });

  var CocktailView = Backbone.View.extend({
    className: 'cocktail',

    events: {
      'click .sources a[href]': 'onSwitchRecipe'
    },

    template: _.template($('#cocktail-template').html()),

    adjustSourcesWidth: function() {
      $('.sources li', this.$el).each(function(idx, source) {
        var label = $(':first-child', source);
        var text = label.attr('data-source');

        label.text(text.substr(0, 1) + '...');
        var maxWidth = source.scrollWidth;

        label.text(text);
        while (source.scrollWidth > maxWidth)
          label.text((text = text.slice(0, -1)) + '...');
      });
    },

    backupScrollPosition: function() {
      return viewport.scrollTop() - $('.sources', this.$el)[0].offsetTop;
    },

    restoreScrollPosition: function(pos) {
      viewport.scrollTop(pos + $('.sources', this.$el)[0].offsetTop);
    },

    render: function() {
      var sources = _.groupBy(
        this.model.get('recipes'),
        function(recipe) { return recipe.source; }
      );

      var recipe = sources[
        this.currentSource || _.keys(sources)[0]
      ][
        this.currentRecipe || 0
      ];

      this.$el.html(this.template({recipe: recipe, sources: sources}));
      return this;
    },

    onSwitchRecipe: function(event) {
      var link = $(event.currentTarget);
      var scrollPos = this.backupScrollPosition();

      this.currentSource = link.attr('data-source');
      this.currentRecipe = link.attr('data-recipe');

      this.setElement(this.render().$el);
      this.adjustSourcesWidth();
      this.restoreScrollPosition(scrollPos);
    }
  });

  var SearchResultsView = Backbone.View.extend({
    el: $('#search-results'),

    initialize : function(options) {
      _.bindAll(this, 'add', 'remove', 'adjustSourcesWidth');

      this.cocktailViews = [];

      this.collection.each(this.add);

      this.collection.bind('add', this.add);
      this.collection.bind('remove', this.remove);
    },

    add: function(cocktail) {
      var view = new CocktailView({model: cocktail});
      view.setElement(view.render().$el.appendTo(this.$el));
      view.adjustSourcesWidth();
      this.cocktailViews.push(view);
    },

    remove: function(cocktail) {
      _.each(this.cocktailViews, function(view) {
        if (view.model == cocktail) {
          view.$el.remove();
          this.cocktailViews = _.without(this.cocktailViews, view);
        }
      });
    },

    adjustSourcesWidth: function() {
      _.invoke(this.cocktailViews, 'adjustSourcesWidth');
    }
  });

  collection = new SearchResults();
  var searchResultsView = new SearchResultsView({collection: collection});

  var results = $('#search-results');
  var form = $('form');
  var viewport = $(window);

  var initial_field = $('input', form).val('');;
  var empty_field = initial_field.clone();
  var original_title = document.title;

  var offset = 0;
  var can_load_more = false;
  var ingredients;

  var state;
  var state_is_volatile;

  var updateTitle = function() {
    var title = original_title;

    if (ingredients.length > 0)
      title += ': ' + ingredients.join(', ');
    document.title = title;
  };

  var prepareField = function(field) {
    field.on('input', function() {
      var has_empty = false;
      var new_state;

      ingredients = [];

      $('input', form).each(function(idx, field) {
        if (field.value != '')
          ingredients.push(field.value);
        else
          has_empty = true;
      });

      new_state  = ingredients.length > 0 ? '#' : '';
      new_state += ingredients.map(encodeURIComponent).join(';');

      if (!has_empty)
        addField();

      if (new_state == state)
        return;

      history[
        state_is_volatile
          ? 'replaceState'
          : 'pushState'
      ](null, null, new_state || '.');

      state = new_state;
      state_is_volatile = true;

      updateTitle();
      collection.query(ingredients);
    });

    field.blur(function() {
      $('input', form).filter(function() {
        return this.value == '';
      }).slice(0, -1).remove();
    });
  };

  var addField = function () {
    var field = empty_field.clone();

    form.append(field);
    prepareField(field);

    return field;
  };

  var populateForm = function() {
    state = document.location.hash;
    state_is_volatile = false;
    ingredients = [];

    var bits = state.substring(1).split(';');

    $('input', form).remove();

    for (var i = 0; i < bits.length; i++) {
      var ingredient = decodeURIComponent(bits[i]);

      if (ingredient == '')
        continue;

      var field = addField();
      field.val(ingredient);

      ingredients.push(ingredient);
    }

    addField().focus();
    updateTitle();
    collection.query(ingredients);
  };

  var adjustSourcesWidthOnResize = function() {
    var width = document.width || window.innerWidth;

    if (width > 580 && width <= 1000)
      // the width of the sources stays constant at
      // a document width of between 581px and 1000px
      var mediaQueryList = matchMedia('(min-width: 581px) and (max-width: 1000px)');
    else
      var mediaQueryList = matchMedia('(width: ' + width + 'px)');

    var listener = function() {
      mediaQueryList.removeListener(listener);
      adjustSourcesWidthOnResize();
      searchResultsView.adjustSourcesWidth();
    };

    mediaQueryList.addListener(listener);
  };

  results.mousedown(function() {
    state_is_volatile = false;
  });

  viewport.scroll(function() {
    state_is_volatile = false;

    if (!collection.canLoadMore)
      return;
    if (viewport.scrollTop() + viewport.height() < $('.cocktail').slice(-5)[0].offsetTop)
      return;

    collection.canLoadMore = false;
    collection.fetch({remove:false, data:{offset:collection.length}});
  });

  viewport.on('online', function() {
    collection.retry();
  });

  viewport.on('popstate', populateForm);

  prepareField(initial_field);
  populateForm();
  adjustSourcesWidthOnResize();
});
