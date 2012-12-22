$(function() {
	var recipes = $('#recipes');
	var form = $('form');
	var viewport = $(window);

	var initial_field = $('input', form);
	var empty_field = initial_field.clone();

	var offset = 0;
	var can_load_more = false;

	var load = function(callback) {
		can_load_more = false;

		jQuery.ajax('/recipes', {
			data: form.serializeArray().concat([{name: 'offset', value: offset}]),
			success: function(data) {
				var elements = $(data);
				var n = elements.filter('.recipe').length;

				callback(elements, n);
				can_load_more = n > 1;
			}
		});
	};

	var loadInitial = function() {
		offset = 0;

		load(function(elements, n) {
			recipes.html(elements);
			offset = n;
		});
	};

	var loadMore = function() {
		load(function(elements, n) {
			recipes.append(elements);
			offset += n;
		});
	};

	var prepareField = function(field) {
		field.keyup(function() {
			var ingredients = [];
			var has_empty = false;

			$('input', form).each(function(idx, field) {
				if (field.value != '')
					ingredients.push(encodeURIComponent(field.value));
				else
					has_empty = true;
			});

			if (ingredients.length > 0)
				history.pushState(null, null, '#' + ingredients.join(';'));
			else
				history.pushState(null, null, '.');

			if(!has_empty)
				addField();

			loadInitial();
		});
		
		field.blur(function() {
			$('input[value=]', form).slice(0, -1).remove();
		});
	};

	var addField = function () {
		var field = empty_field.clone();

		form.append(field);
		prepareField(field);

		return field;
	};

	var populateForm = function() {
		var ingredients = document.location.hash.substring(1).split(';');
		var field = $('input', form).first().val('');

		$('input', form).slice(1).remove();

		for (var i = 0; i < ingredients.length; i++) {
			var ingredient = decodeURIComponent(ingredients[i]);

			if (!ingredient)
				continue;

			field.val(ingredient);
			field = addField();
		}

		field.focus();
		loadInitial();
	};

	viewport.scroll(function() {
		if (!can_load_more)
			return;
		if (viewport.scrollTop() + viewport.height() < $('.recipe').slice(-5)[0].offsetTop)
			return;

		loadMore();
	});

	viewport.on('popstate', populateForm);

	prepareField(initial_field);
	populateForm();
});
