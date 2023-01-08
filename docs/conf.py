# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

build_date = datetime.utcfromtimestamp(
    int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
)
# -- Project information -----------------------------------------------------

project = "cwltest"
copyright = (
    f"2016 - {build_date.year}, Common Workflow Language project and contributors"
)
author = "Common Workflow Language project and contributors"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.inheritance_diagram",
    "autoapi.extension",
    "sphinx_autodoc_typehints",
    "sphinx_rtd_theme",
    "sphinxcontrib.autoprogram",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "schema_salad": ("https://schema-salad.readthedocs.io/en/stable/", None),
    #"rdflib": ("https://rdflib.readthedocs.io/en/6.2.0/", None),
    #"pytest": ("https://docs.pytest.org/en/7.2.x/", None),
    "pytest_xdist": ("https://pytest-xdist.readthedocs.io/en/latest/", None),
    #"ruamel.yaml": ("https://yaml.readthedocs.io/en/stable/", None),
}


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


from pkg_resources import get_distribution

release = get_distribution("cwltest").version
version = ".".join(release.split(".")[:2])

autoapi_dirs = ["../cwltest"]
autodoc_typehints = "description"
autoapi_keep_files = True
autoapi_ignore = ["*.pyi"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-inheritance-diagram",
    "show-module-summary",
    "imported-members",
    "special-members",
]
# sphinx-autodoc-typehints
always_document_param_types = True
# If False, do not add type info for undocumented parameters.
# If True, add stub documentation for undocumented parameters to be able to add type info.
