$(function() {
	var Cocktail = Backbone.Model.extend();

	var SearchResults = Backbone.Collection.extend({
		model: Cocktail,

		url: function() {
			var params = [];

			if (this.index_updated)
				params.push({name: 'index_updated', value: this.index_updated});

			for (var i = 0; i < this.ingredients.length; i++)
				params.push({name: 'ingredient', value: this.ingredients[i]});

			return '/recipes' + (params.length ? '?' + $.param(params) : '');
		},

		parse: function(resp, options) {
			this.canLoadMore = resp.cocktails.length > 0;
			this.index_updated = resp.index_updated;

			return resp.cocktails;
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

	var FirefoxWarningView = Backbone.View.extend({
		el: $('#firefox-warning'),

		render: function() {
			var firefoxVersion = navigator.userAgent.match(/ Firefox\/([\d.]+)/);

			if (firefoxVersion)
			if (!('flex'    in document.body.style))
			if (!('MozFlex' in document.body.style))
				this.$el.html(_.template($('#firefox-warning-template').html(), {
					version: firefoxVersion[1],
					android: navigator.userAgent.indexOf('Android;')    != -1,
					debian:  navigator.userAgent.indexOf(' Iceweasel/') != -1
				}));

			return this;
		}
	});

	var collection = new SearchResults();
	var searchResultsView = new SearchResultsView({collection: collection});

	var firefoxWarningView = new FirefoxWarningView();
	firefoxWarningView.setElement(firefoxWarningView.render());

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

			collection.ingredients = ingredients;
			collection.fetch();
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

		collection.ingredients = ingredients;
		collection.fetch();
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

	viewport.on('popstate', populateForm);

	prepareField(initial_field);
	populateForm();
	adjustSourcesWidthOnResize();
});
