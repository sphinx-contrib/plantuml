PlantUML for Sphinx
===================

Installation
------------

.. code-block::

   pip install sphinxcontrib-plantuml

Usage
-----

Add ``sphinxcontrib.plantuml`` to your extensions list in your ``conf.py``:


.. code-block:: python

   extensions = [
       'sphinxcontrib.plantuml',
   ]

You may also need to specify the plantuml command in your **conf.py**:

.. code-block:: python

   plantuml = 'java -jar /path/to/plantuml.jar'

Instead, you can install a wrapper script in your PATH:

.. code-block:: console

   % cat <<EOT > /usr/local/bin/plantuml
   #!/bin/sh -e
   java -jar /path/to/plantuml.jar "$@"
   EOT
   % chmod +x /usr/local/bin/plantuml

Then, write PlantUML text under the ``.. uml::`` directive::

    .. uml::

       Alice -> Bob: Hi!
       Alice <- Bob: How are you?

or specify path to an external PlantUML file::

    .. uml:: external.uml

You can specify ``height``, ``width``, ``scale`` and ``align``::

    .. uml::
       :scale: 50 %
       :align: center

       Foo <|-- Bar

You can also specify a caption::

    .. uml::
       :caption: Caption with **bold** and *italic*
       :width: 50mm

       Foo <|-- Bar

For details, please see PlantUML_ documentation.

.. _PlantUML: http://plantuml.com/

Configuration
-------------

plantuml
  Path to plantuml executable. (default: 'plantuml')

plantuml_output_format
  Type of output image for HTML renderer. (default: 'png')

  :png: generate only .png inside </img>
  :svg: generate .svg inside <object/> with .png inside </img> as a fallback
  :svg_img: generate only .svg inside <img/> (`browser support <svg_img_>`_)
  :svg_obj: generate only .svg inside <object/> (`browser support <svg_obj_>`_)
  :none: do not generate any images (ignore uml directive)

  When svg is inside <object/> it will always render full size, possibly bigger
  than the container. When svg is inside <img/> it will respect container size
  and scale if necessary.

plantuml_latex_output_format
  Type of output image for LaTeX renderer. (default: 'png')

  :eps: generate .eps (not supported by `pdflatex`)
  :pdf: generate .eps and convert it to .pdf (requires `epstopdf`)
  :png: generate .png
  :tikz: generate .latex in the TikZ format
  :none: do not generate any images (ignore uml directive)

  Because embedded png looks pretty bad, it is recommended to choose `pdf`
  for `pdflatex` or `eps` for `platex`.

plantuml_epstopdf
  Path to epstopdf executable. (default: 'epstopdf')

.. _svg_img: https://caniuse.com/svg-img
.. _svg_obj: https://caniuse.com/svg

plantuml_syntax_error_image
  Should plantuml generate images with render errors. (default: False)

plantuml_cache_path
  Directory where image cache is stored. (default: '_plantuml')

plantuml_batch_size
  **(EXPERIMENTAL)**
  Run plantuml command per the specified number of images. (default: 1)

  If enabled, plantuml documents will be first written to the cache directory,
  and rendered in batches. This eliminates bootstrapping overhead of Java
  runtime and allows plantuml to leverage multiple CPU cores.

  To enable batch rendering, set the size to 100-1000.

Developing
----------

Install the python test dependencies with

.. code-block::

   pip install sphinxcontrib-plantuml[test]

In addition the following non-python dependencies are required in order to run the tests:

* `latexmk`
* `plantuml`
* `texlive`
* `texlive-font-utils`
* `texlive-latex-extra`

The tests can be executed using `pytest`

.. code-block::

    pytest
