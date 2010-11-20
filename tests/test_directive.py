from docutils.parsers.rst import Parser
from docutils.utils import new_document
from docutils.frontend import OptionParser
from sphinx.application import Sphinx
from sphinx.config import Config

from nose.tools import *

from sphinxcontrib import plantuml

class FakeSphinx(Sphinx):
    def __init__(self):
        self.config = Config(None, None, None, None)

def setup():
    global _parser, _settings
    _parser = Parser()
    _settings = OptionParser().get_default_values()
    _settings.tab_width = 8
    _settings.pep_references = False
    _settings.rfc_references = False
    app = FakeSphinx()
    plantuml.setup(app)

def with_parsed(func):
    def test():
        doc = new_document('<test>', _settings)
        src = '\n'.join(l[4:] for l in func.__doc__.splitlines()[2:])
        _parser.parse(src, doc)
        func(doc.children)
    return test

@with_parsed
def test_simple(nodes):
    """Simple UML diagram

    .. uml::

       Alice -> Bob: Hello!
    """
    n = nodes[0]
    assert_equals('Alice -> Bob: Hello!', n['uml'])
    assert n['alt'] is None

@with_parsed
def test_alt(nodes):
    """Alt attribute

    .. uml::
       :alt: Foo <Bar>

       Foo
    """
    n = nodes[0]
    assert_equals('Foo <Bar>', n['alt'])
