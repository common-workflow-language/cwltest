import xml.etree.ElementTree
from pathlib import Path

def parse(
    source: Path = ..., parser: xml.etree.ElementTree.XMLParser = ...
) -> xml.etree.ElementTree.ElementTree: ...
