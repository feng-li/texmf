PYTHON ?= python3
CONVERTER := ./bib_to_html.py

all: snippets publications sync

publications:
	$(PYTHON) $(CONVERTER) --mode full ../publications-feng.bib -o publications-feng.html
	$(PYTHON) $(CONVERTER) --mode full ../publications-yanfei.bib -o publications-yanfei.html
	$(PYTHON) $(CONVERTER) --mode full ../publications-kllab.bib -o publications-kllab.html

snippets:
	$(PYTHON) $(CONVERTER) --mode snippet ../publications-feng.bib -o publications-feng_snippets.html
	$(PYTHON) $(CONVERTER) --mode snippet ../publications-yanfei.bib -o publications-yanfei_snippets.html
	$(PYTHON) $(CONVERTER) --mode snippet ../publications-kllab.bib -o publications-kllab_snippets.html

sync:
	rsync -av publications-feng.html ${HOME}/nextcloud/feng.li/cv/publications.html
