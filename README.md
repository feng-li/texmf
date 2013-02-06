Feng Li's BibTeX database
=========================

Personal BibTeX database


General use of BibTeX
---------------------

    latex file.tex
    bibtex file.aux
    latex file.tex
    latex file.tex

Where to put the BibTeX database
--------------------------------

For a very long time I set up individual database for each paper. Which makes a
lot of duplicated entries. Now I use a general solution, put everything into
the folder (where the environment variable `TEXINPUTS` points to)

    $HOME/texmf/bibtex/bib/myBibTeXFolder

so that the latex program can find the location without specify the
location of the BibTeX database.

Use BibTeX with abbreviations
-----------------------------

Setup three .bib files

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

    \bibliography{abbr,myBibTeX} % no space between files

or

    \bibliography{full,myBibTeX} % no space between files
