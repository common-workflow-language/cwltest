# Stubs for emoji.core (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Text

def emojize(string: Text, use_aliases: bool = ..., delimiters: Any = ...): ...
def demojize(string: Text, delimiters: Any = ...): ...
def get_emoji_regexp(): ...
def emoji_lis(string: Any): ...
