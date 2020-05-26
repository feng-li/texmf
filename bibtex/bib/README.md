Feng Li's BibTeX database
=========================

Feng Li's Personal BibTeX database with interests of Bayesian Statistical Computing,
Forecasting, Econometrics.


General use of BibTeX
---------------------

    latex file.tex
    bibtex file.aux
    latex file.tex
    latex file.tex

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
database everywhere, you could simply issue a command within your paper folder

    bibexport -o for_this_paper_only.bib this_paper.aux

Use BibTeX with abbreviations
-----------------------------

Setup three `.bib` files

    References.bib
    full.bib
    abbr.bib

where `References.bib` contains the main BibTeX entries and `full.bib` contains the
full name strings of journals and `abbr.bib` contains the abbreviations.

We take *Journal of the American Statistical Association* as an example. In
`References.bib` file you write every as usual except in the `journal` entry you
write with a key, e,g

    journal = jasa,

Consequently, in the file `full.bib` you add a line to tell the full name of
the journal

    @String{jasa = {Journal of the American Statistical Association}}

and do the same thing for `abbr.bib` but using the abbreviation

    @String{jasa = {J. Amer. Statist. Assoc.}}


Now in the `file.tex` you choose if you need to use full name or abbreviation as

    \bibliography{abbr,References} % no space between files

or

    \bibliography{full,References} % no space between files
