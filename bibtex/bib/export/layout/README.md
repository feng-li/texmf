# Feng Li's customized html layout

- The original files are from https://github.com/JabRef/jabref/tree/main/src/main/resources/resource/layout

- Installation
  - Open "JabRef GUI -> Options -> Preferences -> Custom export formats".
  - Link to the main layout file and save with an `Export format name` like `mylistrefs`.
  - This saves the preferences in `~/.java/.userPrefs/org/jabref/prefs.xml`.

- Usage

``` shell
    /opt/jabref/bin/JabRef -n -o publications.html,mylistrefs -i publications.bib
```
