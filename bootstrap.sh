#!/bin/sh

set -eu

DIR=$(cd $(dirname $0); pwd)

cd "$DIR/crawler"
for spider in `scrapy list`; do
	scrapy crawl $spider -o $spider.json
done;

cd "$DIR/sphinx"
indexer --all
