# Scrapy settings for cocktails project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'cocktails'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['cocktails.spiders']
NEWSPIDER_MODULE = 'cocktails.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

#DEPTH_LIMIT = 2
