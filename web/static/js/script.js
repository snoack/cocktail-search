$(function() {
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

	var load = function(callback) {
		can_load_more = false;

		jQuery.ajax('/recipes', {
			data: form.serializeArray().concat([{name: 'offset', value: offset}]),
			success: function(data) {
				var elements = $(data);
				var n = elements.filter('.cocktail').length;

				callback(elements, n);
				can_load_more = n > 1;

				$($('.cocktail').slice(-n)).each(function(_, cocktail) {
					var recipes = $('.recipe', cocktail);

					recipes.each(function(_, recipe) {
						$('.sources a', recipe).each(function(idx, source) {
							$(source).click(function(event) {
								var scrollOffset = $('body').scrollTop();
								var recipe = $(recipes[idx]);

								recipes.each(function(_, recipe) {
									recipe = $(recipe);

									if (recipe.hasClass('active')) {
										scrollOffset -= $('.sources', recipe)[0].offsetTop;
										recipe.removeClass('active');
									}
								});

								recipe.addClass('active');
								scrollOffset += $('.sources', recipe)[0].offsetTop;
								viewport.scrollTop(scrollOffset);
							});
						});
					});
				});
			}
		});
	};

	var loadInitial = function() {
		offset = 0;

		load(function(elements, n) {
			results.html(elements);
			offset = n;

			window.scrollTo(0, 0);
			setTimeout(function() { state_is_volatile = true; }, 0);
		});
	};

	var loadMore = function() {
		load(function(elements, n) {
			results.append(elements);
			offset += n;
		});
	};

	var updateTitle = function() {
		var title = original_title;

		if (ingredients.length > 0)
			title += ': ' + ingredients.join(', ');

		document.title = title;
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
		state = document.location.hash;
		state_is_volatile = false;
		ingredients = [];

		var bits = state.substring(1).split(';');
		var field;

		$('input', form).remove();

		for (var i = 0; i < bits.length; i++) {
			var ingredient = decodeURIComponent(bits[i]);

			if (ingredient == '')
				continue;

			field = addField();
			field.val(ingredient);

			ingredients.push(ingredient);
		}

		field = addField();

		// automatically focus the empty field only on webkit browsers. Other
		// browsers hide the placeholder as soon as the field is focused and
		// might confuse users, as they wouldn't know what to enter.
		if ($.browser.webkit)
			field.focus();

		updateTitle();
		loadInitial();
	};

	results.mousedown(function() {
		state_is_volatile = false;
	});

	viewport.scroll(function() {
		state_is_volatile = false;

		if (!can_load_more)
			return;
		if (viewport.scrollTop() + viewport.height() < $('.cocktail').slice(-5)[0].offsetTop)
			return;

		loadMore();
	});

	viewport.on('popstate', populateForm);

	prepareField(initial_field);
	populateForm();
});
