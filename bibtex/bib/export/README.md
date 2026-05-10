# Feng Li's customized html exporter

- The original layout files are from [https://github.com/JabRef/jabref](https://github.com/JabRef/jabref/tree/main/jablib/src/main/resources/resource/layout/listrefs)

- Usage

``` shell
./bib_to_html.py
```

The converter requires the Python package `bibtexparser`. Run
`./bib_to_html.py --help` for all options.

- Common commands

``` shell
./bib_to_html.py
./bib_to_html.py --mode full ../publications-feng.bib
./bib_to_html.py --mode snippet ../publications-feng.bib -o publications-feng_snippets.html
./bib_to_html.py --static --mode snippet ../publications-feng.bib -o publications-feng_static.html
```

Use `--static` to omit JavaScript, quick search, Abstract/Review/BibTeX links,
and hidden Abstract/Review/BibTeX blocks.

- Optional links

Optional link fields are rendered only when present; absent fields are omitted.
Add a `code` field inside any BibLaTeX entry to show a `[Code]` link:

``` bibtex
@article{ZhuX2021LeastSquareApproximation,
  title = {Least-Square Approximation for a Distributed System},
  ...
  url = {https://arxiv.org/abs/1908.04904},
  code = {https://github.com/feng-li/dlsa},
  doi = {10.1080/10618600.2021.1923517}
}
```

- Active layout files
  - `listrefs.begin.layout`
  - `listrefs.end.layout`
  - `listrefs.layout`
  - `listrefs.misc.layout`

`bib_to_html.py` reads the shared begin/end layout files for both full-page and
snippet exports. Snippet output is derived by trimming the document wrapper and
applying snippet-specific CSS defaults.
