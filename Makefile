# Minimal makefile for pdoc documentation
#

# these variables can be set from the command line:
PDOCOPTS  = --docformat numpy
PDOCBUILD = pdoc
SOURCEDIR = src/pumapy/
DESTDIR   = docs/


# our only target at the moment, trigger automatically and unconditionally:
.PHONY: docs

docs:
	$(PDOCBUILD) $(PDOCOPTS) --output-directory "$(DESTDIR)" "$(SOURCEDIR)"