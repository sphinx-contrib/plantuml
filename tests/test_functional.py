import os, tempfile, shutil, glob
from sphinx.application import Sphinx

from nose.tools import *

_fixturedir = os.path.join(os.path.dirname(__file__), 'fixture')
_fakecmd = os.path.join(os.path.dirname(__file__), 'fakecmd.py')
_fakeepstopdf = os.path.join(os.path.dirname(__file__), 'fakeepstopdf.py')

def setup():
    global _tempdir, _srcdir, _outdir
    _tempdir = tempfile.mkdtemp()
    _srcdir = os.path.join(_tempdir, 'src')
    _outdir = os.path.join(_tempdir, 'out')
    os.mkdir(_srcdir)

def teardown():
    shutil.rmtree(_tempdir)

def readfile(fname):
    f = open(os.path.join(_outdir, fname), 'rb')
    try:
        return f.read()
    finally:
        f.close()

def runsphinx(text, builder, confoverrides):
    f = open(os.path.join(_srcdir, 'index.rst'), 'w')
    try:
        f.write(text.encode('utf-8'))
    finally:
        f.close()
    app = Sphinx(_srcdir, _fixturedir, _outdir, _outdir, builder,
                 confoverrides)
    app.build()

def with_runsphinx(builder, **kwargs):
    confoverrides = {'plantuml': _fakecmd, 'plantuml_epstopdf': _fakeepstopdf}
    confoverrides.update(kwargs)
    def wrapfunc(func):
        def test():
            src = '\n'.join(l[4:] for l in func.__doc__.splitlines()[2:])
            os.mkdir(_outdir)
            try:
                runsphinx(src, builder, confoverrides)
                func()
            finally:
                os.unlink(os.path.join(_srcdir, 'index.rst'))
                shutil.rmtree(_outdir)
        test.func_name = func.func_name
        return test
    return wrapfunc

@with_runsphinx('html', plantuml_output_format='svg')
def test_buildhtml_simple_with_svg():
    """Generate simple HTML

    .. uml::

       Hello
    """
    pngfiles = glob.glob(os.path.join(_outdir, '_images', 'plantuml-*.png'))
    assert len(pngfiles) == 1
    svgfiles = glob.glob(os.path.join(_outdir, '_images', 'plantuml-*.svg'))
    assert len(svgfiles) == 1

    assert '<img src="_images/plantuml' in readfile('index.html')
    assert '<object data="_images/plantuml' in readfile('index.html')

    pngcontent = readfile(pngfiles[0]).splitlines()
    assert '-pipe' in pngcontent[0]
    assert_equals('Hello', pngcontent[1])
    svgcontent = readfile(svgfiles[0]).splitlines()
    assert '-tsvg' in svgcontent[0]
    assert_equals('Hello', svgcontent[1])

@with_runsphinx('html')
def test_buildhtml_samediagram():
    """Same diagram should be same file

    .. uml::

       Hello

    .. uml::

       Hello
    """
    files = glob.glob(os.path.join(_outdir, '_images', 'plantuml-*.png'))
    assert len(files) == 1
    imgtags = [l for l in readfile('index.html').splitlines()
               if '<img src="_images/plantuml' in l]
    assert len(imgtags) == 2

@with_runsphinx('html')
def test_buildhtml_alt():
    """Generate HTML with alt specified

    .. uml::
       :alt: Foo <Bar>

       Hello
    """
    assert 'alt="Foo &lt;Bar&gt;"' in readfile('index.html')

@with_runsphinx('html')
def test_buildhtml_nonascii():
    u"""Generate simple HTML of non-ascii diagram

    .. uml::

       \u3042
    """
    files = glob.glob(os.path.join(_outdir, '_images', 'plantuml-*.png'))
    content = readfile(files[0]).splitlines()
    assert '-charset utf-8' in content[0]
    assert_equals(u'\u3042', content[1].decode('utf-8'))

@with_runsphinx('latex')
def test_buildlatex_simple():
    """Generate simple LaTeX

    .. uml::

       Hello
    """
    files = glob.glob(os.path.join(_outdir, 'plantuml-*.png'))
    assert len(files) == 1
    assert r'\includegraphics{plantuml-' in readfile('plantuml_fixture.tex')

    content = readfile(files[0]).splitlines()
    assert '-pipe' in content[0]
    assert_equals('Hello', content[1])

@with_runsphinx('latex', plantuml_latex_output_format='eps')
def test_buildlatex_simple_with_eps():
    """Generate simple LaTeX with EPS

    .. uml::

       Hello
    """
    files = glob.glob(os.path.join(_outdir, 'plantuml-*.eps'))
    assert len(files) == 1
    assert r'\includegraphics{plantuml-' in readfile('plantuml_fixture.tex')

    content = readfile(files[0]).splitlines()
    assert '-teps' in content[0]
    assert_equals('Hello', content[1])

@with_runsphinx('latex', plantuml_latex_output_format='pdf')
def test_buildlatex_simple_with_pdf():
    """Generate simple LaTeX with PDF

    .. uml::

       Hello
    """
    epsfiles = glob.glob(os.path.join(_outdir, 'plantuml-*.eps'))
    pdffiles = glob.glob(os.path.join(_outdir, 'plantuml-*.pdf'))
    assert len(epsfiles) == 1
    assert len(pdffiles) == 1
    assert r'\includegraphics{plantuml-' in readfile('plantuml_fixture.tex')

    epscontent = readfile(epsfiles[0]).splitlines()
    assert '-teps' in epscontent[0]
    assert_equals('Hello', epscontent[1])
    pdfcontent = readfile(pdffiles[0]).splitlines()
    assert os.path.basename(epsfiles[0]) in pdfcontent[0]
