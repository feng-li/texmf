Feng Li's BibTeX database
=========================

Feng Li's Personal BibTeX database with interests of Bayesian Statistical Computing,
Forecasting, and Econometrics.

Where to put the BibTeX database
--------------------------------

For a very long time I set up individual BibTeX database for each paper which yields a lot
of duplicated entries. Now I use a general solution, put everything into the folder (where
the environment variable `BIBINPUTS` points to)

    $HOME/texmf/bibtex/bib/myBibTeXFolder

so that the latex program can find the location without specifying the location of the
BibTeX database.


Collaborate with coauthors
--------------------------

If you want to collaborate with other people but do not want to copy your big BibTeX
database everywhere, you could simply issue a command within your paper folder when your
final version is done.

### `BibTeX`

    bibexport -o <for_this_paper_only>.bib <this_paper>.aux

### `BibLaTeX`

    biber --output_format=bibtex --output_resolve <this_paper>.bcf

    \bibliography{abbr,References} % no space between files

or

    \bibliography{full,References} % no space between files
