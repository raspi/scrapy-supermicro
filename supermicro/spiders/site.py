# -*- coding: utf-8 -*-
import scrapy
import re

from supermicro.items import Motherboard


def cleantxt(v: str) -> str:
    v = v.replace("Intel", "")
    v = v.replace("AMD", "")
    v = v.replace("\u2122", "")  # tm
    v = v.replace("\u00ae", "")  # (c)
    v = v.replace("\u2021", "")  #

    v = ' '.join(v.split())
    v = v.strip()
    return v


class BaseSpider(scrapy.Spider):
    """
    Base spider, not to be used directly
    """

    allowed_domains = [
        'supermicro.com',
        'www.supermicro.com',
    ]

    start_urls = [
        'https://www.supermicro.com/en/'
    ]

    def parse(self, response: scrapy.http.Response):
        """
        Implemented in actual spider which does something
        """
        raise NotImplementedError

    def parse_motherboard(self, response: scrapy.http.Response):
        """
        Get motherboard specifications
        """

        if '/en/products/motherboard/' not in response.url:
            return

        # Product ID
        sku = response.xpath("/html/head/title/text()").get().split("|")[0].strip()

        # Product image
        img = response.xpath("//div[@class='img-display']//img/@src").get()

        data = Motherboard({
            "_id": sku,
            "_url": response.url,
            "_image": img,
            "_socket": "Unknown socket"
        })

        for table in response.xpath("//td[@class='specHeader']/../.."):
            main_title = table.xpath(".//td[@class='specHeader']/text()").get().strip()
            collected = {}

            for feature in table.xpath(".//td[contains(@class, 'feature')]/.."):
                feature_name = "".join(feature.xpath("td[contains(@class, 'feature')]/span/text()").getall()).strip()

                collected[feature_name] = {}

                ditem = []

                for item in feature.xpath("td[contains(@class, 'description')]/ul/li"):
                    x = "".join(item.xpath(".//text()").getall()).strip()
                    x = x.replace("\u2122", "")  # tm
                    x = x.replace("\u00ae", "")  # (c)
                    x = x.replace("\u2021", "")  #
                    x = x.strip()
                    x = x.strip(",")
                    x = x.strip()

                    ditem.append(x)

                if len(ditem) == 1:
                    # Array -> string
                    ditem = ditem[0]

                collected[feature_name] = ditem

            data[main_title] = collected

        # Rename Processor/Cache -> Processor/Chipset
        if 'Processor/Cache' in data:
            if 'Processor/Chipset' in data:
                raise KeyError("Processor/Chipset exists??")

            data['Processor/Chipset'] = data['Processor/Cache']
            del data['Processor/Cache']

        # Fix form factor naming
        formfactor = data['Physical Stats']['Form Factor']

        if formfactor == "Micro-ATX":
            formfactor = "mATX"
        elif formfactor == "microATX":
            formfactor = "mATX"

        data['Physical Stats']['Form Factor'] = formfactor

        # Get CPU and socket info
        cpuinfo = data['Processor/Chipset']['CPU']

        if isinstance(cpuinfo, list):
            socket = cpuinfo[1].split(",")[0]
            data["_socket"] = socket
        else:
            data["_socket"] = cpuinfo.split(",")[0]

        data["_socket"] = data["_socket"].replace("supported", "").strip()

        countsearch = ['Single', 'Dual', 'Quad', 'Octal']

        if data["_socket"].split(" ")[0] not in countsearch:
            data["_socket"] = "Single " + data["_socket"]

        data["_socket_count"] = data["_socket"].split(" ")[0]

        # Remove first word ('Single', 'Dual', 'Quad', 'Octal')
        data["_socket"] = " ".join(data["_socket"].split(" ")[1:])

        data["_socket"] = data["_socket"].replace(
            "2nd Gen Intel Xeon Scalable Processors and Intel Xeon Scalable Processors",
            "LGA3647"
        )

        data["_socket"] = data["_socket"].replace("Socket ", "")
        data["_socket"] = data["_socket"].replace("Socket", "")

        # Fix various socket naming schemes to single one
        data["_socket"] = data["_socket"].replace("LGA 1150", "LGA1150")
        data["_socket"] = data["_socket"].replace("LGA-1150 (H3)", "LGA1150")

        data["_socket"] = data["_socket"].replace("LGA 1151", "LGA1151")
        data["_socket"] = data["_socket"].replace("LGA-1151 (H4)", "LGA1151")
        data["_socket"] = data["_socket"].replace("H4 (LGA1151)", "LGA1151")

        data["_socket"] = data["_socket"].replace("H2 (LGA 1155)", "LGA1155")
        data["_socket"] = data["_socket"].replace("LGA-1155 (H2)", "LGA1155")

        data["_socket"] = data["_socket"].replace("LGA-1200 (H5)", "LGA1200")

        data["_socket"] = data["_socket"].replace("LGA-2011 (R)", "LGA2011")
        data["_socket"] = data["_socket"].replace("R (LGA 2011)", "LGA2011")
        data["_socket"] = data["_socket"].replace("R1 (LGA 2011)", "LGA2011-1")
        data["_socket"] = data["_socket"].replace("R3 (LGA 2011)", "LGA2011-3")
        data["_socket"] = data["_socket"].replace("LGA-2011-3 (R3)", "LGA2011-3")

        data["_socket"] = data["_socket"].replace("R4 (LGA 2066)", "LGA2066")
        data["_socket"] = data["_socket"].replace("LGA-2066 (R4)", "LGA2066")

        data["_socket"] = data["_socket"].replace("LGA-3647 (P)", "LGA3647")

        data["_socket"] = data["_socket"].replace("SoC Processor", "")

        data["_socket"] = cleantxt(data["_socket"])

        data["_socket"] = data["_socket"].replace("Xeon Processor ", "")

        data["_socket"] = data["_socket"].replace(
            "and Xeon Scalable Processors",
            "and 1st Gen Xeon Scalable Processors"
        )

        data["_socket"] = data["_socket"].replace("Processors", "")

        data["_socket"] = cleantxt(data["_socket"])

        yield data


class MatrixSpider(BaseSpider):
    """
    Parse motherboard matrix page
    """
    name = 'matrix'
    start_urls = [
        # 'https://www.supermicro.com/en/products/motherboards/matrix',
        'https://www.supermicro.com/en/sites/default/files/motherboards/search?generation=all&corenum=all'
    ]

    def parse(self, response: scrapy.http.Response):
        boarddata_tpl = {}

        for header in response.xpath("//table[@class='display']/thead/tr/th"):
            name = header.xpath("text()").get().strip()
            boarddata_tpl[name] = None

        for board in response.xpath("//table[@class='display']/tbody/tr"):
            tmp = {}

            for idx, key in enumerate(boarddata_tpl):
                info = "".join(board.xpath(f"./td[{idx + 1}]//text()").getall()).strip()
                tmp[key] = info

            yield scrapy.Request(
                response.urljoin(f"/en/products/motherboard/{tmp['Motherboard']}"),
                callback=self.parse_motherboard,
            )


class MotherboardsSpider(BaseSpider):
    """
    Parse motherboards search page
    """
    name = 'all'
    start_urls = [
        'https://www.supermicro.com/sites/default/files/system/search?block=productselectorblock_21&lang=en&family=motherboards&page=all&currentpage=1'
    ]

    def parse(self, response: scrapy.http.Response):
        for sku in response.xpath("//div/@data-sku").getall():
            yield scrapy.Request(
                response.urljoin(f"/en/products/motherboard/{sku}"),
                callback=self.parse_motherboard,
            )


class MotherboardSpider(BaseSpider):
    """
    Parse specific motherboard
    """
    name = 'mb'
    start_urls = [
        'https://www.supermicro.com/en/products/motherboard/'
    ]

    prodid = None

    def __init__(self, mb: str = None):

        if mb == "":
            mb = None

        if mb is None:
            raise ValueError("No MB model given")

        self.prodid = mb

        self.start_urls = [
            f"https://www.supermicro.com/en/products/motherboard/{mb}",
        ]

    def parse(self, response: scrapy.http.Response):
        yield scrapy.Request(
            response.url,
            callback=self.parse_motherboard,
        )


class QuickReferenceMotherboardManualSpider(BaseSpider):
    """
    Get motherboard quick reference manuals
    """
    name = 'quickrefs'
    start_urls = [
        'https://www.supermicro.com/support/quickrefs/?mlg=0'
    ]

    def parse(self, response: scrapy.http.Response):
        yield scrapy.FormRequest(
            response.url,
            callback=self.parse_qrefs,
            formdata={
                "Category": "MBD",
                "List": "1",
            },
            #meta={
            #    # 'dont_cache': True,
            #},
        )

    def parse_qrefs(self, response: scrapy.http.Response):
        boarddata_tpl = {}

        srctable = response.xpath("//table[contains(@class, 'support-table')]")

        lang = ""
        for hdr in srctable.xpath("./thead/tr/th"):
            name = "".join(hdr.xpath(".//text()").getall()).strip()
            name = name.rstrip(".")

            if name not in ['Products', 'Type', 'Rev']:
                lang = name

            if name == 'Rev':
                name = lang + " " + name

            if name not in boarddata_tpl:
                boarddata_tpl[name] = None
            else:
                raise KeyError(f"key {name} exists!")

        for prod in srctable.xpath("./tbody/tr"):
            tmp = {
                'manual': {},
            }

            for idx, key in enumerate(boarddata_tpl):
                x = prod.xpath(f"./td[{idx + 1}]")
                link = x.xpath(".//a/@href").get()
                if link is not None:
                    link = link.replace("javascript:redirect", "")
                    link = link.lstrip("(")
                    link = link.lstrip("'")
                    link = link.rstrip(";")
                    link = link.rstrip(")")
                    link = link.rstrip("'")
                    info = link.strip()
                else:
                    info = "".join(x.xpath(f".//text()").getall()).strip()

                if info == "":
                    info = None

                if key in ['Products', 'Type']:
                    tmp[key] = info
                else:
                    tmp['manual'][key] = info

            for k in tmp['manual']:
                if tmp['manual'][k] is None:
                    continue

                if tmp['manual'][k].find("/") == 0:
                    yield scrapy.Request(
                        response.urljoin(tmp['manual'][k]),
                        callback=self.parse_disc,
                        #formdata={
                        #    "Agree": "ACCEPT",
                        #},
                        meta={
                            'name': tmp['Products'],
                        }
                    )

    def parse_disc(self, response: scrapy.http.Response):
        print()
        print()
