# -*- coding: utf-8 -*-
"""
    sphinxcontrib.plantuml
    ~~~~~~~~~~~~~~~~~~~~~~

    Embed PlantUML diagrams on your documentation.

    :copyright: Copyright 2010 by Yuya Nishihara <yuya@tcha.org>.
    :license: BSD, see LICENSE for details.
"""

import codecs
import errno
import hashlib
import io
import os
import re
import shlex
import subprocess
import time
from contextlib import contextmanager
from ftplib import FTP
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from sphinx.errors import SphinxError
from sphinx.util.nodes import set_source_info
from sphinx.util.osutil import (
    ensuredir,
    ENOENT,
)

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from sphinx.util.i18n import search_image_for_language
except ImportError:  # Sphinx < 1.4
    def search_image_for_language(filename, env):
        return filename

try:
    from sphinx.util import logging
    logger = logging.getLogger(__name__)
    def _warn(self, msg):
        logger.warning(msg)
except (AttributeError, ImportError):  # Sphinx < 1.6
    def _warn(self, msg):
        self.builder.warn(msg)


class PlantUmlError(SphinxError):
    pass


class plantuml(nodes.General, nodes.Element):
    pass


class PlantumlFtp:
    def __init__(self, env, node, fileformat, url='127.0.0.1', port=4242):
        self.env = env
        self.node = node
        self.fileformat = fileformat
        self.url = url
        self.port = port
        self.ftp = FTP()
        self.is_connected = False
        self.connection_try = 0
        self.connection_try_max = 5
        self.server_process = None

    def start_server(self):
        """Cares about starting an extra process for the ftp server"""
        server_args = generate_plantuml_args(self.env, self.node, self.fileformat)
        server_args.extend(['-ftp'])
        self.server_process = subprocess.Popen(server_args,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('PlantUML server started')

    def stop_server(self):
        """Kills hard the server"""
        self.server_process.terminate()
        logger.info('PlantUML server stopped')
        # Give the system some time to close/terminate the process.
        # This is important, if sphinx gets executed several times in a row (e.g. during tests).
        # In this case it can happen, that the startup of the next ftp-server iteration is before the
        # system has terminated the old process. Then the newer process gets terminated with the termination
        # of the old process.
        time.sleep(0.5)

    def connect(self):
        """Connects the client part to the server"""
        # Server may not yet be running. So lets try it several times.
        # Should only be needed for first image, after that server is up all the time.
        while not self.is_connected and self.connection_try < self.connection_try_max:
            self.connection_try += 1
            try:
                self.ftp.connect(self.url, self.port)
                self.ftp.login()
                self.ftp.set_pasv(False)
                self.is_connected = True
            except ConnectionRefusedError:
                logger.info(f'Plantuml FTP connection refused. Trying again... '
                            f'[{self.connection_try}/{self.connection_try_max}]')
                time.sleep(0.2)
        logger.info('Plantuml FTP connection accepted')

    def generate(self, input, output_file):
        """
        Generates plantuml image based on a given input(text).
        The result is stored in a given file handler.
        """
        file_upload = io.BytesIO(input)
        # Get the pure filename (no path, no extension) and use it
        # as unique name for the upload and download
        file_name = Path(output_file.name).stem
        file_ext = Path(output_file.name).suffix
        self.ftp.storbinary(f"STOR {file_name}.txt", file_upload)
        self.ftp.retrbinary(f'RETR {file_name}{file_ext}', output_file.write)
        # Delete uploaded and generated files, otherwise they will be kept
        # in memory till the server stops running.
        # Do not try to delete the files by its file names.
        # This will only delete their content, but not the file itself (known bug).
        self.ftp.sendcmd(f'DELE *.*')


PLANTUML_FTP_SERVER = None


def align(argument):
    align_values = ('left', 'center', 'right')
    return directives.choice(argument, align_values)


def html_format(argument):
    format_values = list(_KNOWN_HTML_FORMATS.keys())
    return directives.choice(argument, format_values)


def latex_format(argument):
    format_values = list(_KNOWN_LATEX_FORMATS.keys())
    return directives.choice(argument, format_values)


class UmlDirective(Directive):
    """Directive to insert PlantUML markup

    Example::

        .. uml::
           :alt: Alice and Bob

           Alice -> Bob: Hello
           Alice <- Bob: Hi
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    option_spec = {
        'alt': directives.unchanged,
        'align': align,
        'caption': directives.unchanged,
        'height': directives.length_or_unitless,
        'html_format': html_format,
        'latex_format': latex_format,
        'name': directives.unchanged,
        'scale': directives.percentage,
        'width': directives.length_or_percentage_or_unitless,
    }

    def run(self):
        warning = self.state.document.reporter.warning
        env = self.state.document.settings.env
        if self.arguments and self.content:
            return [warning('uml directive cannot have both content and '
                            'a filename argument', line=self.lineno)]
        if self.arguments:
            fn = search_image_for_language(self.arguments[0], env)
            relfn, absfn = env.relfn2path(fn)
            env.note_dependency(relfn)
            try:
                umlcode = _read_utf8(absfn)
            except (IOError, UnicodeDecodeError) as err:
                return [warning('PlantUML file "%s" cannot be read: %s'
                                % (fn, err), line=self.lineno)]
        else:
            relfn = env.doc2path(env.docname, base=None)
            umlcode = '\n'.join(self.content)

        node = plantuml(self.block_text, **self.options)
        node['uml'] = umlcode
        node['incdir'] = os.path.dirname(relfn)
        node['filename'] = os.path.split(relfn)[1]

        # XXX maybe this should be moved to _visit_plantuml functions. it
        # seems wrong to insert "figure" node by "plantuml" directive.
        if 'caption' in self.options or 'align' in self.options:
            node = nodes.figure('', node)
            if 'align' in self.options:
                node['align'] = self.options['align']
        if 'caption' in self.options:
            inodes, messages = self.state.inline_text(self.options['caption'],
                                                      self.lineno)
            caption_node = nodes.caption(self.options['caption'], '', *inodes)
            caption_node.extend(messages)
            set_source_info(self, caption_node)
            node += caption_node
        self.add_name(node)
        if 'html_format' in self.options:
            node['html_format'] = self.options['html_format']
        if 'latex_format' in self.options:
            node['latex_format'] = self.options['latex_format']

        return [node]


def _read_utf8(filename):
    fp = codecs.open(filename, 'rb', 'utf-8')
    try:
        return fp.read()
    finally:
        fp.close()


def generate_name(self, node, fileformat):
    h = hashlib.sha1()
    # may include different file relative to doc
    h.update(node['incdir'].encode('utf-8'))
    h.update(b'\0')
    h.update(node['uml'].encode('utf-8'))
    key = h.hexdigest()
    fname = 'plantuml-%s.%s' % (key, fileformat)
    imgpath = getattr(self.builder, 'imgpath', None)
    if imgpath:
        return ('/'.join((self.builder.imgpath, fname)),
                os.path.join(self.builder.outdir, '_images', fname))
    else:
        return fname, os.path.join(self.builder.outdir, fname)


def _ntunquote(s):
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


def _split_cmdargs(args):
    if isinstance(args, (tuple, list)):
        return list(args)
    if os.name == 'nt':
        return list(map(_ntunquote, shlex.split(args, posix=False)))
    else:
        return shlex.split(args, posix=True)


_ARGS_BY_FILEFORMAT = {
    'eps': ['-teps'],
    'png': [],
    'svg': ['-tsvg'],
    'txt': ['-ttxt'],
}


def generate_plantuml_args(self, node, fileformat):
    args = _split_cmdargs(self.builder.config.plantuml)
    args.extend(['-pipe', '-charset', 'utf-8'])
    args.extend(['-filename', node['filename']])
    args.extend(_ARGS_BY_FILEFORMAT[fileformat])
    return args


def render_plantuml(self, node, fileformat):
    refname, outfname = generate_name(self, node, fileformat)
    if os.path.exists(outfname):
        return refname, outfname  # don't regenerate
    absincdir = os.path.join(self.builder.srcdir, node['incdir'])
    ensuredir(os.path.dirname(outfname))
    f = open(outfname, 'wb')

    try:
        # FTP Mode
        if self.builder.config.plantuml_use_ftp_mode:
            # If not yet done, start FTP server and store its instance globally.
            # So it can be reused by later generation calls.
            # Should get executed only once during a build.
            global PLANTUML_FTP_SERVER
            if not PLANTUML_FTP_SERVER:
                PLANTUML_FTP_SERVER = PlantumlFtp(self, node, fileformat,
                                                  url=self.builder.config.plantuml_ftp_url,
                                                  port=self.builder.config.plantuml_ftp_port)
                if self.builder.config.plantuml_spawn_ftp_server:
                    PLANTUML_FTP_SERVER.start_server()
                PLANTUML_FTP_SERVER.connect()

            PLANTUML_FTP_SERVER.generate(node['uml'].encode('utf-8'), f)
            return refname, outfname
        # Normal Mode
        else:
            try:
                p = subprocess.Popen(generate_plantuml_args(self, node,
                                                            fileformat),
                                     stdout=f, stdin=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     cwd=absincdir)
            except OSError as err:
                if err.errno != ENOENT:
                    raise
                raise PlantUmlError('plantuml command %r cannot be run'
                                    % self.builder.config.plantuml)
            serr = p.communicate(node['uml'].encode('utf-8'))[1]
            if p.returncode != 0:
                if self.builder.config.plantuml_syntax_error_image:
                    _warn(self, 'error while running plantuml\n\n%s' % serr)
                else:
                    raise PlantUmlError('error while running plantuml\n\n%s' % serr)
            return refname, outfname
    finally:
        f.close()


def render_plantuml_inline(self, node, fileformat):
    absincdir = os.path.join(self.builder.srcdir, node['incdir'])
    try:
        p = subprocess.Popen(generate_plantuml_args(self, node, fileformat),
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             cwd=absincdir)
    except OSError as err:
        if err.errno != ENOENT:
            raise
        raise PlantUmlError('plantuml command %r cannot be run'
                            % self.builder.config.plantuml)
    sout, serr = p.communicate(node['uml'].encode('utf-8'))
    if p.returncode != 0:
        raise PlantUmlError('error while running plantuml\n\n%s' % serr)
    return sout.decode('utf-8')


def _get_png_tag(self, fnames, node):
    refname, outfname = fnames['png']
    alt = node.get('alt', node['uml'])

    # mimic StandaloneHTMLBuilder.post_process_images(). maybe we should
    # process images prior to html_vist.
    scale_attrs = [k for k in ('scale', 'width', 'height') if k in node]
    if scale_attrs and Image is None:
        _warn(self, ('plantuml: unsupported scaling attributes: %s '
                     '(install PIL or Pillow)'
                     % ', '.join(scale_attrs)))
    if not scale_attrs or Image is None:
        return ('<img src="%s" alt="%s"/>\n'
                % (self.encode(refname), self.encode(alt)))

    scale = node.get('scale', 100)
    styles = []

    # Width/Height
    vu = re.compile(r"(?P<value>\d+)\s*(?P<units>[a-zA-Z%]+)?")
    for a in ['width', 'height']:
        if a not in node:
            continue
        m = vu.match(node[a])
        if not m:
            raise PlantUmlError('Invalid %s' % a)
        m = m.groupdict()
        w = int(m['value'])
        wu = m['units'] if m['units'] else 'px'
        styles.append('%s: %s%s' % (a, w * scale / 100, wu))

    # Add physical size to assist rendering (defaults)
    if not styles:
        # the image may be corrupted if platuml isn't configured correctly,
        # which isn't a hard error.
        try:
            im = Image.open(outfname)
            im.load()
            styles.extend('%s: %s%s' % (a, w * scale / 100, 'px')
                          for a, w in zip(['width', 'height'], im.size))
        except (IOError, OSError) as err:
            _warn(self, 'plantuml: failed to get image size: %s' % err)

    return ('<a href="%s"><img src="%s" alt="%s" style="%s"/>'
            '</a>\n'
            % (self.encode(refname),
               self.encode(refname),
               self.encode(alt),
               self.encode('; '.join(styles))))


def _get_svg_style(fname):
    f = codecs.open(fname, 'r', 'utf-8')
    try:
        for l in f:
            m = re.search(r'<svg\b([^<>]+)', l)
            if m:
                attrs = m.group(1)
                break
        else:
            return
    finally:
        f.close()

    m = re.search(r'\bstyle=[\'"]([^\'"]+)', attrs)
    if not m:
        return
    return m.group(1)


def _get_svg_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    return '\n'.join([
        # copy width/height style from <svg> tag, so that <object> area
        # has enough space.
        '<object data="%s" type="image/svg+xml" style="%s">' % (
            self.encode(refname), _get_svg_style(outfname) or ''),
        _get_png_tag(self, fnames, node),
        '</object>'])


def _get_svg_img_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    alt = node.get('alt', node['uml'])
    return ('<img src="%s" alt="%s"/>'
            % (self.encode(refname), self.encode(alt)))


def _get_svg_obj_tag(self, fnames, node):
    refname, outfname = fnames['svg']
    # copy width/height style from <svg> tag, so that <object> area
    # has enough space.
    return ('<object data="%s" type="image/svg+xml" style="%s"></object>'
            % (self.encode(refname), _get_svg_style(outfname) or ''))


_KNOWN_HTML_FORMATS = {
    'png': (('png',), _get_png_tag),
    'svg': (('png', 'svg'), _get_svg_tag),
    'svg_img': (('svg',), _get_svg_img_tag),
    'svg_obj': (('svg',), _get_svg_obj_tag),
}


@contextmanager
def _prepare_html_render(self, fmt):
    if fmt == 'none':
        raise nodes.SkipNode

    try:
        try:
            fileformats, gettag = _KNOWN_HTML_FORMATS[fmt]
        except KeyError:
            raise PlantUmlError(
                'plantuml_output_format must be one of %s, but is %r'
                % (', '.join(map(repr, _KNOWN_HTML_FORMATS)), fmt))

        yield fileformats, gettag

    except PlantUmlError as err:
        _warn(self, str(err))
        raise nodes.SkipNode


def html_visit_plantuml(self, node):
    if 'html_format' in node:
        fmt = node['html_format']
    else:
        fmt = self.builder.config.plantuml_output_format

    with _prepare_html_render(self, fmt) as (fileformats, gettag):
        # fnames: {fileformat: (refname, outfname), ...}
        fnames = dict((e, render_plantuml(self, node, e))
                      for e in fileformats)

    self.body.append(self.starttag(node, 'p', CLASS='plantuml'))
    self.body.append(gettag(self, fnames, node))
    self.body.append('</p>\n')
    raise nodes.SkipNode


def _convert_eps_to_pdf(self, refname, fname):
    args = _split_cmdargs(self.builder.config.plantuml_epstopdf)
    args.append(fname)
    try:
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        except OSError as err:
            # workaround for missing shebang of epstopdf script
            if err.errno != getattr(errno, 'ENOEXEC', 0):
                raise
            p = subprocess.Popen(['bash'] + args, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    except OSError as err:
        if err.errno != ENOENT:
            raise
        raise PlantUmlError('epstopdf command %r cannot be run'
                            % self.builder.config.plantuml_epstopdf)
    serr = p.communicate()[1]
    if p.returncode != 0:
        raise PlantUmlError('error while running epstopdf\n\n%s' % serr)
    return refname[:-4] + '.pdf', fname[:-4] + '.pdf'


_KNOWN_LATEX_FORMATS = {
    'eps': ('eps', lambda self, refname, fname: (refname, fname)),
    'pdf': ('eps', _convert_eps_to_pdf),
    'png': ('png', lambda self, refname, fname: (refname, fname)),
}


def latex_visit_plantuml(self, node):
    if 'latex_format' in node:
        fmt = node['latex_format']
    else:
        fmt = self.builder.config.plantuml_latex_output_format
    if fmt == 'none':
        raise nodes.SkipNode
    try:
        try:
            fileformat, postproc = _KNOWN_LATEX_FORMATS[fmt]
        except KeyError:
            raise PlantUmlError(
                'plantuml_latex_output_format must be one of %s, but is %r'
                % (', '.join(map(repr, _KNOWN_LATEX_FORMATS)), fmt))
        refname, outfname = render_plantuml(self, node, fileformat)
        refname, outfname = postproc(self, refname, outfname)
    except PlantUmlError as err:
        _warn(self, str(err))
        raise nodes.SkipNode

    # put node representing rendered image
    img_node = nodes.image(uri=refname, **node.attributes)
    img_node.delattr('uml')
    if not img_node.hasattr('alt'):
        img_node['alt'] = node['uml']
    node.append(img_node)


def latex_depart_plantuml(self, node):
    pass


def confluence_visit_plantuml(self, node):
    fmt = self.builder.config.plantuml_output_format
    with _prepare_html_render(self, fmt) as (fileformats, _):
        _, outfname = render_plantuml(self, node, fileformats[0])

    # Create a new image node in the document
    img_node = nodes.image(uri=outfname, **node.attributes)
    img_node.delattr('uml')
    img_node.document = node.document
    img_node.parent = node.parent
    node.parent.children.insert(node.parent.children.index(node), img_node)
    if not img_node.hasattr('alt'):
        img_node['alt'] = node['uml']

    # Confluence builder needs to be aware of the new asset
    from sphinxcontrib.confluencebuilder import ConfluenceLogger
    ConfluenceLogger.info('re-scanning for assets... ', nonl=0)
    self.assets.process(list(self.assets.env.all_docs.keys()))
    ConfluenceLogger.info('done\n')

    # Handle the new node as a regular image
    return self.visit_image(img_node)


def text_visit_plantuml(self, node):
    try:
        text = render_plantuml_inline(self, node, 'txt')
    except PlantUmlError as err:
        _warn(self, str(err))
        text = node['uml']  # fall back to uml text, which is still readable

    self.new_state()
    self.add_text(text)
    self.end_state()
    raise nodes.SkipNode


def pdf_visit_plantuml(self, node):
    try:
        refname, outfname = render_plantuml(self, node, 'eps')
        refname, outfname = _convert_eps_to_pdf(self, refname, outfname)
    except PlantUmlError as err:
        _warn(self, str(err))
        raise nodes.SkipNode
    rep = nodes.image(uri=outfname, alt=node.get('alt', node['uml']))
    node.parent.replace(node, rep)


def unsupported_visit_plantuml(self, node):
    _warn(self, 'plantuml: unsupported output format (node skipped)')
    raise nodes.SkipNode


_NODE_VISITORS = {
    'html': (html_visit_plantuml, None),
    'latex': (latex_visit_plantuml, latex_depart_plantuml),
    'man': (unsupported_visit_plantuml, None),  # TODO
    'texinfo': (unsupported_visit_plantuml, None),  # TODO
    'text': (text_visit_plantuml, None),
    'confluence': (confluence_visit_plantuml, None),
}


def stop_ftp_server(app, exception):
    if app.config.plantuml_use_ftp_mode:
        global PLANTUML_FTP_SERVER
        if PLANTUML_FTP_SERVER:
            PLANTUML_FTP_SERVER.stop_server()
            # Important: Set PLANTUML_FTP_SERVER to None.
            # Needed for tests, otherwise the next test may find an already set PLANTUML_FTP_SERVER
            # and therefore doesn't start the server.
            PLANTUML_FTP_SERVER = None


def setup(app):
    app.add_node(plantuml, **_NODE_VISITORS)
    app.add_directive('uml', UmlDirective)
    try:
        app.add_config_value('plantuml', 'plantuml', 'html',
                             types=(str, tuple, list))
    except TypeError:
        # Sphinx < 1.4?
        app.add_config_value('plantuml', 'plantuml', 'html')
    app.add_config_value('plantuml_output_format', 'png', 'html')
    app.add_config_value('plantuml_epstopdf', 'epstopdf', '')
    app.add_config_value('plantuml_latex_output_format', 'png', '')
    app.add_config_value('plantuml_syntax_error_image', False, '')
    app.add_config_value('plantuml_use_ftp_mode', False, '')
    app.add_config_value('plantuml_ftp_url', '127.0.0.1', '')
    app.add_config_value('plantuml_ftp_port', 4242, '')
    app.add_config_value('plantuml_spawn_ftp_server', True, '')

    app.connect('build-finished', stop_ftp_server)

    # imitate what app.add_node() does
    if 'rst2pdf.pdfbuilder' in app.config.extensions:
        from rst2pdf.pdfbuilder import PDFTranslator as translator
        setattr(translator, 'visit_' + plantuml.__name__, pdf_visit_plantuml)

    return {'parallel_read_safe': True}
