from scrapy.item import Item, Field

class CocktailItem(Item):
	title = Field()
	picture = Field()
	url = Field()
	source = Field()
	ingredients = Field()

	# will be indexed too, but not shown in the list. Primary for
	# ingredients of ingredients like infusions on seriouseats.com
	extra_ingredients = Field()
