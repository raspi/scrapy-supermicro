# -*- coding: utf-8 -*-
import os
import json
from tempfile import NamedTemporaryFile
from pathlib import Path
from shutil import move
import re

import scrapy

from supermicro.items import *


class SupermicroPipeline:
    def process_item(self, item: object, spider: scrapy.Spider):

        basepath = os.path.abspath(os.path.join("..", "items"))
        fullpath = None

        if isinstance(item, Motherboard):
            fname = item['_id'] + ".json"
            formfactor = item['Physical Stats']['Form Factor']
            basepath = os.path.abspath(os.path.join(basepath, "MB", item['_socket_count'], item['_socket'], formfactor))
            fullpath = os.path.abspath(os.path.join(basepath, fname))

        if fullpath is not None:
            if not isinstance(item, dict):
                return

            Path(basepath).mkdir(parents=True, exist_ok=True)

            if os.path.isfile(fullpath):
                spider.logger.warning(f"file '{fullpath}' exists, skipping!")
                return

            # Save to temporary file
            tmpf = NamedTemporaryFile("w", prefix="supermicro-item-", suffix=".json", encoding="utf8", delete=False)
            with tmpf as f:
                json.dump(item, f)
                f.flush()
                spider.logger.info(f"saved as {f.name}")

            # Rename and move the temporary file to actual file
            newpath = move(tmpf.name, fullpath)
            spider.logger.info(f"renamed {tmpf.name} to {newpath}")
