import os
import random
from string import ascii_lowercase, ascii_uppercase, digits
from typing import Any

import aiofiles
import ujson
from sanic import Sanic
from jinja2 import Environment

from .ihacache import ihateanimeCache


class ihaSanic(Sanic):
    """A derivative version for iha CDN."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dcache: ihateanimeCache
        self.jinja2env: Environment


async def read_files(fpath, dont_convert=False):
    """Read a files
    ---

    :param fpath: file path
    :type fpath: str
    :return: file contents, parsed with ujson if it's list or dict
             if file doesn't exist, return None
    :rtype: Any
    """
    if not os.path.isfile(fpath):
        return None
    async with aiofiles.open(fpath, "r", encoding="utf-8") as fp:
        file_contents = await fp.read()
    if not dont_convert:
        try:
            file_contents = ujson.loads(file_contents)
        except ValueError:
            pass
    return file_contents


async def write_files(data: Any, fpath: str):
    """Write data to files
    ---

    :param data: data to write, can be any
    :type data: Any
    :param fpath: file path
    :type fpath: str
    """
    if isinstance(data, (dict, list, tuple)):
        data = ujson.dumps(
            data, ensure_ascii=False, encode_html_chars=False, escape_forward_slashes=False, indent=4,
        )
    elif isinstance(data, int):
        data = str(data)
    wmode = "w"
    if isinstance(data, bytes):
        wmode = "wb"
    args = [fpath, wmode]
    kwargs = {}
    if wmode == "w":
        kwargs["encoding"] = "utf-8"
    async with aiofiles.open(*args, **kwargs) as fpw:
        await fpw.write(data)


def generate_custom_code(
    length: int = 8, include_numbers: bool = False, include_uppercase: bool = False
) -> str:
    """Generate a random custom code to be used by anything.

    :param length: int: the code length
    :param include_numbers: bool: include numbers in generated code or not.
    :param include_uppercase: bool: include uppercased letters in generated code or not.
    :return: a custom generated string that could be used for anything.
    :rtype: str
    """
    letters_used = ascii_lowercase
    if include_numbers:
        letters_used += digits
    if include_uppercase:
        letters_used += ascii_uppercase
    generated = "".join([random.choice(letters_used) for _ in range(length)])  # nosec
    return generated


def humanbytes(B):
    if B is None:
        return B
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776
    PB = float(KB ** 5)

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KiB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MiB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GiB".format(B / GB)
    elif TB <= B < PB:
        return "{0:.2f} TiB".format(B / TB)
    return "{0:.2f} PiB".format(B / PB)
