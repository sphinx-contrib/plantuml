PlantUML Example
================

Class diagram:

.. uml::
   :caption: A caption with **bold** text

   Foo <|-- Bar

Sequence diagram:

.. uml::

   Alice -> Bob: Hello!
   Alice <- Bob: Hi!

Sequence diagram in Japanese, read from external file:

.. uml:: seq.ja.uml

scale: 50%:

.. uml::
   :scale: 50 %

   Foo <|-- Bar

width: 50%:

.. uml::
   :width: 50 %

   Foo <|-- Bar

height: 400px:

.. uml::
   :height: 400px

   Foo <|-- Bar

width: 10px * 1000%:

.. uml::
   :scale: 1000 %
   :width: 10px

   Foo <|-- Bar

200x600px:

.. uml::
   :width:  200px
   :height: 600px

   Foo <|-- Bar
