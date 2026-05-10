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
from typing import Iterable

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
    "doi",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a BibTeX/BibLaTeX file to the local HTML publication layout."
    )
    parser.add_argument("bibfile", type=Path, help="Input .bib file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output HTML file")
    parser.add_argument(
        "--mode",
        choices=("full", "snippet"),
        default="full",
        help="Use the full-page wrapper or snippet wrapper",
    )
    parser.add_argument(
        "--order",
        choices=("date-desc", "input"),
        default="date-desc",
        help="Entry ordering for the generated list",
    )
    return parser.parse_args()


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


def pages_for_display(value: str) -> str:
    return clean(value).replace("--", "-")


def entry_type_label(entry: dict[str, str]) -> str:
    entry_type = clean(entry.get("ENTRYTYPE")).lower()
    return ENTRYTYPE_LABELS.get(entry_type, entry_type.capitalize())


def render_links(entry: dict[str, str], key: str) -> str:
    links = []
    if field(entry, "abstract"):
        links.append(
            f"""[<a href="javascript:toggleInfo('{html_attr(key)}','abstract')">Abstract</a>]"""
        )
    if field(entry, "review"):
        links.append(
            f"""[<a href="javascript:toggleInfo('{html_attr(key)}','review')">Review</a>]"""
        )

    links.append(
        f"""[<a href="javascript:toggleInfo('{html_attr(key)}','bibtex')">BibTeX</a>]"""
    )

    doi = field(entry, "doi")
    if doi:
        links.append(
            f"""[<a href="{html_attr(doi_url(doi))}" target="_blank">DOI</a>]"""
        )

    url = field(entry, "url")
    if url:
        links.append(
            f"""[<a href="{html_attr(url)}" target="_blank">Preprint</a>]"""
        )

    return " ".join(links)


def render_summary(entry: dict[str, str]) -> str:
    people = format_people(field(entry, "author")) or format_people(field(entry, "editor"))
    title = html_text(field(entry, "title"))
    pieces = [f"""{html_text(people)} ({html_text(field(entry, "year"))}). <i>"{title}". </i>"""]

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
        pieces.append(f" {html_text(address)}")

    volume = field(entry, "volume")
    if volume:
        pieces.append(f" Vol. {html_text(volume)} ")

    number = field(entry, "number")
    if number:
        pieces.append(f"({html_text(number)}), ")

    pages = field(entry, "pages")
    if pages:
        pieces.append(f"pp. {html_text(pages_for_display(pages))}.")

    publisher = field(entry, "publisher")
    if publisher:
        pieces.append(f" {html_text(publisher)}")

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


def render_entry(entry: dict[str, str]) -> str:
    key = field(entry, "ID")
    abstract = field(entry, "abstract")
    review = field(entry, "review")

    parts = [
        "<li>",
        (
            f"""  <div id="{html_attr(key)}" data-reftype="{html_attr(entry_type_label(entry))}" """
            f"""class="bibitem">{render_summary(entry)}"""
        ),
        f"""  <p class="infolinks">{render_links(entry, key)}</p>""",
        "  </div>",
    ]

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
                f"\t<td><strong>Review</strong>: {html_text(review)}</td>",
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


def wrapper_paths(mode: str) -> tuple[Path, Path]:
    base = Path(__file__).resolve().parent / "layout"
    if mode == "snippet":
        layout_dir = base / "snippets"
    else:
        layout_dir = base / "ordered"
    return layout_dir / "listrefs.begin.layout", layout_dir / "listrefs.end.layout"


def render_document(entries: list[dict[str, str]], mode: str, order: str) -> str:
    begin_path, end_path = wrapper_paths(mode)
    begin = begin_path.read_text(encoding="utf-8").replace("\\encoding", "UTF-8")
    end = end_path.read_text(encoding="utf-8")
    today = dt.date.today().strftime("%d/%m/%Y")
    end = end.replace("\\format[CurrentDate]{dd/MM/yyyy}", today)
    end = end.replace(
        'Created by <a href="http://jabref.sourceforge.net">JabRef</a>',
        "Created by bib_to_html.py",
    )
    end = end.replace("<!-- file generated by JabRef -->", "<!-- file generated by bib_to_html.py -->")

    body = "\n".join(render_entry(entry) for entry in ordered_entries(entries, order))
    return begin.rstrip() + "\n" + body + "\n" + end.lstrip()


def main() -> None:
    args = parse_args()
    html_document = render_document(load_entries(args.bibfile), args.mode, args.order)
    args.output.write_text(html_document, encoding="utf-8")


if __name__ == "__main__":
    main()
