#!/usr/bin/env python3
"""Generate JabRef-like HTML bibliography exports.

This intentionally implements only the layout subset used by this repository.
It accepts BibTeX and BibLaTeX input, normalizes the field names used by the
local layouts, and writes either a full standalone page or an embeddable snippet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path
from typing import Iterable, Sequence

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from bibtexparser.customization import splitname


ENTRYTYPE_LABELS = {
    "article": "Article",
    "book": "Book",
    "inbook": "InBook",
    "incollection": "InCollection",
    "inproceedings": "InProceedings",
    "proceedings": "Proceedings",
    "thesis": "Thesis",
}

FIELD_ALIASES = {
    "address": ("address", "location"),
    "booktitle": ("booktitle", "eventtitle"),
    "journal": ("journal", "journaltitle"),
    "school": ("school", "institution"),
}

BIB_BLOCK_FIELDS = (
    "author",
    "editor",
    "title",
    "booktitle",
    "journal",
    "publisher",
    "school",
    "year",
    "volume",
    "number",
    "pages",
    "edition",
    "note",
    "url",
    "code",
    "doi",
)

OPTIONAL_LINK_FIELDS = (
    ("doi", "DOI"),
    ("url", "Preprint"),
    ("software", "Software"),
)

BOLD_AUTHOR_NAMES = {"feng li"}

DEFAULT_BIB_GLOB = "publications-*.bib"
DEFAULT_SNIPPET_SUFFIX = "_snippets"


class HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help or ""
        if not action.option_strings:
            return help_text
        if "%(default)" in help_text:
            return help_text
        if action.default is argparse.SUPPRESS or action.default is None:
            return help_text
        return help_text + " (default: %(default)s)"


FULL_BODY_CSS = (
    "body { background-color: white; font-family: Arial, sans-serif; font-size: 13px; "
    "line-height: 1.2; padding: 1em; color: #2E2E2E; width: 50em; margin: auto auto; }"
)

SNIPPET_CSS_REPLACEMENTS = {
    FULL_BODY_CSS: (
        "body { background-color: white; font-size: auto; line-height: auto; "
        "padding: 1em; color: auto; width: auto; margin: auto auto; }"
    ),
    "form#quicksearch { width: auto; border-style: solid; border-color: gray; border-width: 1px 0px; padding: 0.7em 0.5em; display:none; position:relative; }": (
        "form#quicksearch { width: auto; border-style: solid; border-color: auto; "
        "border-width: 1px 0px; padding: 0.7em 0.5em; display:none; position:relative; }"
    ),
    'input[type="button"] { background-color: #efefef; border: 1px #2E2E2E solid;}': (
        'input[type="button"] { background-color: auto; border: 1px #2E2E2E solid;}'
    ),
    "li a { color: navy; text-decoration: none; }\n": "",
    "li div.highlight { background-color: #EFEFEF; border-top: 2px #2E2E2E solid; font-weight: bold; }": (
        "li div.highlight { background-color: auto; border-top: 2px #2E2E2E solid; font-weight: bold; }"
    ),
    "li div.abstract, li div.review, li div.bibtex { background-color: #EFEFEF; text-align: justify; }": (
        "li div.abstract, li div.review, li div.bibtex {width: 100%; color: darkblue; "
        "background-color: darkgray; text-align: justify; }"
    ),
    "    font-size: 12px;": "    font-size: 12pt;",
    "    margin: 0;": "    margin: 1em;",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert BibTeX/BibLaTeX publication files to local HTML exports.",
        formatter_class=HelpFormatter,
        epilog="""examples:
  ./bib_to_html.py
      Generate full and snippet HTML for all ../publications-*.bib files.

  ./bib_to_html.py --mode full ../publications-feng.bib
      Generate publications-feng.html in this script's directory.

  ./bib_to_html.py --mode snippet ../publications-feng.bib -o /tmp/feng.html
      Generate one snippet file at an explicit path.

  ./bib_to_html.py --static --mode snippet ../publications-feng.bib -o /tmp/feng.html
      Generate a static snippet without JavaScript, quick search, Abstract, or BibTeX toggles.
""",
    )
    parser.add_argument(
        "bibfiles",
        nargs="*",
        type=Path,
        metavar="BIBFILE",
        help=(
            "Input .bib file(s). If omitted, all ../publications-*.bib files "
            "are converted."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("full", "snippet", "both"),
        default="both",
        help="Output variant to generate",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Output HTML file. Only valid with exactly one input file and "
            "--mode full or --mode snippet."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for automatically named output files (default: this script's directory)",
    )
    parser.add_argument(
        "--default-glob",
        default=DEFAULT_BIB_GLOB,
        metavar="GLOB",
        help="Glob used in the parent directory when no BIBFILE is given",
    )
    parser.add_argument(
        "--snippet-suffix",
        default=DEFAULT_SNIPPET_SUFFIX,
        help="Suffix added to automatically named snippet files",
    )
    parser.add_argument(
        "--order",
        choices=("date-desc", "input"),
        default="date-desc",
        help="Entry ordering for the generated list",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help=(
            "Export only the static publication list: omit JavaScript, quick search, "
            "Abstract/Review/BibTeX links, and hidden Abstract/Review/BibTeX blocks"
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Do not print generated output paths",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned outputs without writing files",
    )

    args = parser.parse_args()
    if args.output and (len(args.bibfiles) != 1 or args.mode == "both"):
        parser.error("-o/--output requires exactly one BIBFILE and --mode full or --mode snippet")
    return args


def default_bibfiles(pattern: str) -> list[Path]:
    input_dir = Path(__file__).resolve().parent.parent
    return sorted(input_dir.glob(pattern))


def resolve_bibfiles(args: argparse.Namespace) -> list[Path]:
    bibfiles = args.bibfiles or default_bibfiles(args.default_glob)
    if not bibfiles:
        raise SystemExit(f"No input files matched ../{args.default_glob}")
    missing = [str(path) for path in bibfiles if not path.exists()]
    if missing:
        raise SystemExit("Input file(s) not found: " + ", ".join(missing))
    return bibfiles


def selected_modes(mode: str) -> tuple[str, ...]:
    if mode == "both":
        return ("full", "snippet")
    return (mode,)


def default_output_path(bibfile: Path, mode: str, output_dir: Path, snippet_suffix: str) -> Path:
    suffix = "" if mode == "full" else snippet_suffix
    return output_dir / f"{bibfile.stem}{suffix}.html"


def output_path_for(
    bibfile: Path,
    mode: str,
    args: argparse.Namespace,
) -> Path:
    if args.output:
        return args.output
    output_dir = args.output_dir or Path(__file__).resolve().parent
    return default_output_path(bibfile, mode, output_dir, args.snippet_suffix)


def load_entries(path: Path) -> list[dict[str, str]]:
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.homogenize_fields = False
    parser.customization = convert_to_unicode

    with path.open(encoding="utf-8") as handle:
        database = bibtexparser.load(handle, parser=parser)

    entries = database.entries
    for index, entry in enumerate(entries):
        entry["_index"] = str(index)
    return entries


def clean(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\n", " ")
    value = value.replace("$<$", "<").replace("$>$", ">")
    value = value.replace("~ ", "\u00a0").replace("~", "\u00a0")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def annotation_items(entry: dict[str, str]) -> dict[str, str]:
    value = entry.get("annotation")
    if not value:
        return {}

    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\\\\s*", "\n", text)

    items: dict[str, str] = {}
    current_key = ""
    current_value: list[str] = []

    def save_current() -> None:
        if current_key:
            parsed_value = clean(" ".join(current_value))
            if parsed_value:
                items[current_key] = parsed_value

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match:
            save_current()
            current_key = match.group(1).lower()
            current_value = [match.group(2)]
        elif current_key:
            current_value.append(line)

    save_current()
    return items


def annotation_value(entry: dict[str, str], key: str) -> str:
    return annotation_items(entry).get(key.lower(), "")


def contribution_text(entry: dict[str, str]) -> str:
    value = annotation_value(entry, "contribution")
    if value.startswith("(") and value.endswith(")"):
        return value[1:-1].strip()
    return value


def field(entry: dict[str, str], name: str) -> str:
    if name == "year":
        return year(entry)

    for candidate in FIELD_ALIASES.get(name, (name,)):
        value = clean(entry.get(candidate))
        if value:
            return value
    return ""


def year(entry: dict[str, str]) -> str:
    value = clean(entry.get("year"))
    if value:
        return value
    match = re.match(r"(\d{4})", clean(entry.get("date")))
    return match.group(1) if match else ""


def date_parts(entry: dict[str, str]) -> tuple[int, int, int]:
    value = clean(entry.get("date")) or clean(entry.get("year"))
    match = re.match(r"(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", value)
    if not match:
        return (0, 0, 0)
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def html_text(value: str) -> str:
    return html.escape(clean(value), quote=False)


def html_attr(value: str) -> str:
    return html.escape(clean(value), quote=True)


def split_names(value: str) -> list[str]:
    names: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(value):
        char = value[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(depth - 1, 0)
        elif depth == 0 and value[i : i + 5] == " and ":
            names.append(value[start:i].strip())
            start = i + 5
            i += 4
        i += 1
    last = value[start:].strip()
    if last:
        names.append(last)
    return names


def format_name(name: str) -> str:
    name = clean(name).strip("{}")
    if not name:
        return ""
    try:
        parts = splitname(name, strict_mode=False)
    except Exception:
        return name

    first = parts.get("first", [])
    von = parts.get("von", [])
    last = parts.get("last", [])
    jr = parts.get("jr", [])
    tokens = [*first, *jr, *von, *last]
    return clean(" ".join(tokens)) or name


def format_people(value: str) -> str:
    names = [format_name(name) for name in split_names(value)]
    names = [name for name in names if name]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def format_people_html(value: str) -> str:
    names = [format_name(name) for name in split_names(value)]
    names = [name for name in names if name]
    rendered = []
    for name in names:
        rendered_name = html_text(name)
        if name.casefold() in BOLD_AUTHOR_NAMES:
            rendered_name = f"<strong>{rendered_name}</strong>"
        rendered.append(rendered_name)

    if not rendered:
        return ""
    if len(rendered) == 1:
        return rendered[0]
    return ", ".join(rendered[:-1]) + " and " + rendered[-1]


def strip_doi(value: str) -> str:
    doi = clean(value)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi


def doi_url(value: str) -> str:
    doi = clean(value)
    if re.match(r"https?://", doi, flags=re.IGNORECASE):
        return doi
    return f"https://doi.org/{strip_doi(doi)}"


def external_link_url(name: str, value: str) -> str:
    if name == "doi":
        return doi_url(value)
    return value


def first_url(value: str) -> str:
    text = clean(value)
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"(https?://[^\s<>{}]+/)\s+([^\s<>{}]+)", r"\1\2", text)

    match = re.search(r"https?://[^\s<>{}]+", text)
    if match:
        return match.group(0).rstrip(".,;")
    return text


def optional_link_value(entry: dict[str, str], name: str) -> str:
    if name == "software":
        return first_url(
            field(entry, "software")
            or field(entry, "code")
            or annotation_value(entry, "software")
        )
    return field(entry, name)


def external_anchor(url: str, label: str) -> str:
    return (
        f"""<a href="{html_attr(url)}" target="_blank" """
        f"""rel="noopener noreferrer">{html_text(label)}</a>"""
    )


def pages_for_display(value: str) -> str:
    return clean(value).replace("--", "-")


def entry_type_label(entry: dict[str, str]) -> str:
    entry_type = clean(entry.get("ENTRYTYPE")).lower()
    return ENTRYTYPE_LABELS.get(entry_type, entry_type.capitalize())


def render_links(entry: dict[str, str], key: str, static: bool = False) -> str:
    links = []
    if not static and field(entry, "abstract"):
        links.append(
            f"""[<a href="javascript:toggleInfo('{html_attr(key)}','abstract')">Abstract</a>]"""
        )
    if not static and field(entry, "review"):
        links.append(
            f"""[<a href="javascript:toggleInfo('{html_attr(key)}','review')">Review</a>]"""
        )

    if not static:
        links.append(
            f"""[<a href="javascript:toggleInfo('{html_attr(key)}','bibtex')">BibTeX</a>]"""
        )

    for name, label in OPTIONAL_LINK_FIELDS:
        value = optional_link_value(entry, name)
        if not value:
            continue
        links.append(f"[{external_anchor(external_link_url(name, value), label)}]")

    return " ".join(links)


def render_summary(entry: dict[str, str]) -> str:
    people = format_people_html(field(entry, "author")) or format_people_html(field(entry, "editor"))
    title = html_text(field(entry, "title"))
    pieces = [f"""{people} ({html_text(field(entry, "year"))}). <i>"{title}". </i>"""]

    journal = field(entry, "journal")
    if journal:
        pieces.append(f"<strong>{html_text(journal)}</strong>, ")

    booktitle = field(entry, "booktitle")
    if booktitle:
        pieces.append(f"In <strong>{html_text(booktitle)}</strong>. ")

    howpublished = field(entry, "howpublished")
    if howpublished:
        pieces.append(f"{html_text(howpublished)},")

    school = field(entry, "school")
    if school:
        pieces.append(f" Thesis at: <strong>{html_text(school)}</strong>.")

    address = field(entry, "address")
    if address:
        suffix = " " if field(entry, "pages") and not field(entry, "volume") else ""
        pieces.append(f" {html_text(address)}{suffix}")

    volume = field(entry, "volume")
    number = field(entry, "number")
    if volume:
        suffix = " " if number else ""
        if not number and field(entry, "pages"):
            suffix = ", "
        pieces.append(f" Vol. {html_text(volume)}{suffix}")

    if number:
        pieces.append(f"({html_text(number)}), ")

    pages = field(entry, "pages")
    if pages:
        pieces.append(f"pp. {html_text(pages_for_display(pages))}.")

    publisher = field(entry, "publisher")
    if publisher:
        pieces.append(f" {html_text(publisher)}")

    contribution = contribution_text(entry)
    if contribution:
        pieces.append(f"""<br><span class="contribution">[<u>{html_text(contribution)}</u>]</span>""")

    return "".join(pieces)


def bib_field_value(entry: dict[str, str], name: str) -> str:
    if name == "doi":
        return strip_doi(field(entry, "doi"))
    return field(entry, name)


def render_bib_block(entry: dict[str, str], key: str) -> str:
    entry_type = clean(entry.get("ENTRYTYPE")).lower() or "misc"
    lines = [f"@{entry_type}{{{key},"]
    for name in BIB_BLOCK_FIELDS:
        value = bib_field_value(entry, name)
        if value:
            lines.append(f"  {name} = {{{html_text(value)}}}")
    lines.append("}")
    rendered = [lines[0]]
    rendered.extend(f"{line}," for line in lines[1:-2])
    if len(lines) > 2:
        rendered.append(lines[-2])
    rendered.append(lines[-1])
    return "\n".join(rendered)


def render_entry(entry: dict[str, str], static: bool = False) -> str:
    key = field(entry, "ID")
    abstract = field(entry, "abstract")
    review = field(entry, "review")
    links = render_links(entry, key, static)

    if static:
        parts = [
            (
                f"""<li id="{html_attr(key)}" data-reftype="{html_attr(entry_type_label(entry))}" """
                f"""class="bibitem">{render_summary(entry)}"""
            ),
        ]
        if links:
            parts.append(f"""  <p class="infolinks">{links}</p>""")
        parts.append("</li>")
        return "\n".join(parts)

    parts = [
        "<li>",
        (
            f"""  <div id="{html_attr(key)}" data-reftype="{html_attr(entry_type_label(entry))}" """
            f"""class="bibitem">{render_summary(entry)}"""
        ),
    ]
    if links:
        parts.append(f"""  <p class="infolinks">{links}</p>""")
    parts.append("  </div>")

    if abstract:
        parts.extend(
            [
                "",
                f"""<div id="abs_{html_attr(key)}" class="abstract noshow">""",
                f"\t<strong>Abstract</strong>: {html_text(abstract)}",
                "</div>",
            ]
        )

    if review:
        parts.extend(
            [
                f"""<div id="rev_{html_attr(key)}" class="review noshow">""",
                f"\t<strong>Review</strong>: {html_text(review)}",
                "</div>",
            ]
        )

    parts.extend(
        [
            f"""<div id="bib_{html_attr(key)}" class="bibtex noshow">""",
            "<strong>BibTeX</strong>:",
            '<pre class="bib">',
            render_bib_block(entry, key),
            "</pre></div>",
            "</li>",
        ]
    )
    return "\n".join(parts)


def ordered_entries(entries: Iterable[dict[str, str]], order: str) -> list[dict[str, str]]:
    result = list(entries)
    if order == "input":
        return result
    return sorted(
        result,
        key=lambda entry: (*date_parts(entry), int(entry["_index"])),
        reverse=True,
    )


def wrapper_paths() -> tuple[Path, Path]:
    base = Path(__file__).resolve().parent / "layout"
    return base / "listrefs.begin.layout", base / "listrefs.end.layout"


def normalize_javascript(begin: str) -> str:
    return begin.replace(
        r'return str.replace(/[-\\[\\]\\/\\{\\}\\(\\)\\*\\+\\?\\.\\\\\\^\\$\\|]/g, "\\\\$&");',
        r'return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");',
    )


def strip_dynamic_layout(begin: str) -> str:
    begin = re.sub(
        r'\n?<script type="text/javascript">.*?</script>\n?',
        "\n",
        begin,
        flags=re.S,
    )
    begin = re.sub(
        r'\n?<form action="" id="quicksearch">.*?</form>\n?',
        "\n",
        begin,
        flags=re.S,
    )
    begin = re.sub(r"\n?\.bib \{.*?\n\}\n?", "\n", begin, flags=re.S)

    dynamic_css_markers = (
        "quicksearch",
        "searchstat",
        "settings",
        "showsettings",
        "invalidsearch",
        'input[type="button"]',
        "li.noshow",
        "li div.noshow",
        "li div.highlight",
        "li div.abstract",
        "li div.bibtex",
        "t.bibtex",
    )
    return "\n".join(
        line for line in begin.splitlines() if not any(marker in line for marker in dynamic_css_markers)
    )


def layout_begin_for_mode(begin: str, mode: str, static: bool) -> str:
    begin = normalize_javascript(begin).replace("\\encoding", "UTF-8")
    if mode == "snippet":
        start_tag = '<style type="text/css">' if static else '<script type="text/javascript">'
        begin = begin[begin.index(start_tag) :]
        begin = begin.replace("</head>\n<body>\n\n", "")
        for old, new in SNIPPET_CSS_REPLACEMENTS.items():
            begin = begin.replace(old, new)
    if static:
        begin = strip_dynamic_layout(begin)
    if mode == "full":
        return begin
    return begin


def layout_end_for_mode(end: str, mode: str) -> str:
    today = dt.date.today().strftime("%d/%m/%Y")
    end = end.replace("\\format[CurrentDate]{dd/MM/yyyy}", today)
    end = end.replace(
        'Created by <a href="http://jabref.sourceforge.net">JabRef</a>',
        "Created by bib_to_html.py",
    )
    end = end.replace(
        "<!-- file generated by JabRef -->", "<!-- file generated by bib_to_html.py -->"
    )
    if mode == "snippet" and "<footer>" in end:
        end = end[: end.index("<footer>")]
    return end


def render_document(
    entries: list[dict[str, str]], mode: str, order: str, static: bool
) -> str:
    begin_path, end_path = wrapper_paths()
    begin = layout_begin_for_mode(begin_path.read_text(encoding="utf-8"), mode, static)
    end = layout_end_for_mode(end_path.read_text(encoding="utf-8"), mode)

    body = "\n".join(
        render_entry(entry, static) for entry in ordered_entries(entries, order)
    )
    return begin.rstrip() + "\n" + body + "\n" + end.lstrip()


def convert_file(bibfile: Path, modes: Sequence[str], args: argparse.Namespace) -> list[Path]:
    entries = load_entries(bibfile)
    outputs: list[Path] = []
    for mode in modes:
        output = output_path_for(bibfile, mode, args)
        outputs.append(output)
        if args.dry_run:
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        html_document = render_document(entries, mode, args.order, args.static)
        output.write_text(html_document, encoding="utf-8")
    return outputs


def main() -> None:
    args = parse_args()
    modes = selected_modes(args.mode)
    generated: list[Path] = []
    for bibfile in resolve_bibfiles(args):
        generated.extend(convert_file(bibfile, modes, args))

    if not args.quiet:
        verb = "would write" if args.dry_run else "wrote"
        for output in generated:
            print(f"{verb} {output}")


if __name__ == "__main__":
    main()
