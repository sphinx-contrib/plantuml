PYTHON = python
TWINE = twine

.PHONY: dist
dist:
	$(PYTHON) setup.py sdist

.PHONY: upload
upload: dist
	$(TWINE) upload dist/*

.PHONY: clean
clean:
	$(PYTHON) setup.py clean

.PHONY: distclean
distclean: clean
	$(RM) -R build dist *.egg-info
