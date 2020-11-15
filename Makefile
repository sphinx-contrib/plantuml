FAKEROOT = fakeroot
PYTHON = python3
TWINE = twine

.PHONY: dist
dist:
	$(FAKEROOT) $(PYTHON) setup.py sdist

.PHONY: upload
upload: dist
	$(TWINE) upload dist/*

.PHONY: check
check:
	$(PYTHON) `which nosetests`

.PHONY: clean
clean:
	$(PYTHON) setup.py clean

.PHONY: distclean
distclean: clean
	$(RM) -R build dist *.egg-info
