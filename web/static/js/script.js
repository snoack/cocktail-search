$(function() {
	var recipes = $('#recipes');
	var form = $('form');
	var viewport = $(window);

	var initial_field = $('input', form);
	var empty_field = initial_field.clone();

	var offset = 0;
	var can_load_more = false;

	var ingredients;
	var state;

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

	var updateHistory = function() {
		if (state != document.location.hash)
			history.pushState(null, null, state || '.');
	};

	var prepareField = function(field) {
		field.keyup(function() {
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

			if (new_state != state) {
				state = new_state;
				loadInitial();
			}
		});

		field.blur(function() {
			$('input[value=]', form).slice(0, -1).remove();
			updateHistory();
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
		ingredients = [];

		var bits = state.substring(1).split(';');

		$('input', form).remove();

		for (var i = 0; i < bits.length; i++) {
			var ingredient = decodeURIComponent(bits[i]);

			if (ingredient == '')
				continue;

			field = addField();
			field.val(ingredient);

			ingredients.push(ingredient);
		}

		addField().focus();
		loadInitial();
	};

	viewport.scroll(function() {
		if (!can_load_more)
			return;
		if (viewport.scrollTop() + viewport.height() < $('.recipe').slice(-5)[0].offsetTop)
			return;

		loadMore();
	});

	viewport.on('mousemove', updateHistory);
	viewport.on('popstate', populateForm);

	prepareField(initial_field);
	populateForm();
});
