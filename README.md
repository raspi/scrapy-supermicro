# scrapy-supermicro

Web crawler for Supermicro ([supermicro.com](https://supermicro.com/)) web site.

## Requirements

* Python
* [Scrapy](https://scrapy.org/)

## Notes

* 30 day cache is used in `settings.py`

## Spiders

Everything is downloaded to `items` directory.

### Motherboards

Download all motherboard specifications as JSON files

    scrapy crawl all

### Single motherboard

Download single motherboard's specifications as JSON file

    scrapy crawl mb -a mb="X11SPH-nCTPF"
