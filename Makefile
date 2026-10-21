FAKEROOT = fakeroot
PYTHON = python3
TWINE = twine

.PHONY: dist
dist:
	$(FAKEROOT) $(PYTHON) -m build

.PHONY: upload
upload: dist
	$(TWINE) upload dist/*

.PHONY: check
check:
	$(PYTHON) -m pytest

.PHONY: clean
clean:
	$(RM) -R build

.PHONY: distclean
distclean: clean
	$(RM) -R build dist *.egg-info
