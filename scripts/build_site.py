"""Build the static GitHub Pages site from the report folders.

Only the HTML report and local files it references are published. The source
folders themselves remain untouched.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
OUTPUT = ROOT / "dist"
PHOTO_CATALOGUE = ROOT / "scripts" / "bird_photos.json"
SKIP_FOLDERS = {".git", ".github", "site", "scripts", "dist"}
STAMP = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})")
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_NO_REFERRER = "referrerPolicy: 'no-referrer',"
OSM_SITE_REFERRER = "referrerPolicy: 'strict-origin-when-cross-origin',"
OSM_NO_REFERRER_NOTE = re.compile(
    r"(?P<indent>^[ \t]*)/\* Opened from file://.*?\*/\s*"
    r"(?=referrerPolicy: 'no-referrer',)",
    re.MULTILINE | re.DOTALL,
)


class LocalReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: set[str] = set()
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.in_style = tag == "style"
        for name, value in attrs:
            if not value:
                continue
            if name in {"src", "href", "poster"}:
                self.references.add(value)
            elif name == "srcset":
                for candidate in value.split(","):
                    self.references.add(candidate.strip().split(" ")[0])
            elif name == "style":
                self.references.update(match.group(2) for match in CSS_URL.finditer(value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.references.update(match.group(2) for match in CSS_URL.finditer(data))


class FirstHeading(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_heading = False
        self.parts: list[str] = []
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1" and self.title is None:
            self.in_heading = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self.in_heading:
            self.title = re.sub(r"\s+", " ", "".join(self.parts)).strip()
            self.in_heading = False

    def handle_data(self, data: str) -> None:
        if self.in_heading:
            self.parts.append(data)


class RankedDetections(HTMLParser):
    """Read species rows in the order shown in a report's detection list."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.list_depth = 0
        self.rows: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        attributes = dict(attrs)
        if self.list_depth:
            if self.list_depth == 1 and "detection" in (attributes.get("class") or "").split():
                self.rows.append(attributes)
            self.list_depth += 1
        elif attributes.get("id") == "detection-list":
            self.list_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self.list_depth:
            self.list_depth -= 1


def report_heading(report: Path) -> str | None:
    parser = FirstHeading()
    parser.feed(report.read_text(encoding="utf-8"))
    return parser.title


def leading_bird(report: Path, photos: dict[str, dict[str, str]]) -> dict | None:
    """Choose the report's highest-confidence species; ties keep report order."""
    html = report.read_text(encoding="utf-8")
    parser = RankedDetections()
    parser.feed(html)
    try:
        top = max(parser.rows, key=lambda row: float(row["data-conf"]))
        confidence = float(top["data-conf"])
        count = int(top["data-count"])
        ranked_scientific = top["data-sci"]
    except (ValueError, KeyError, TypeError):
        return None

    match = re.search(r"window\.SESSION_DATA\s*=\s*(\{.*?\})\s*;\s*</script>", html, re.DOTALL)
    if not match:
        return None
    try:
        detections = json.loads(match.group(1))["detections"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(detections, list):
        return None

    valid = [item for item in detections if isinstance(item, dict) and item.get("sci") and item.get("common")]
    if not valid:
        return None
    selected = next((item for item in valid if item["sci"].casefold() == ranked_scientific.casefold()), None)
    if selected is None:
        return None
    scientific = selected["sci"]
    return {
        "common": selected["common"],
        "scientific": scientific,
        "detections": count,
        "confidence": confidence,
        "photo": photos.get(scientific),
    }


def references_in(source: Path) -> set[str]:
    suffix = source.suffix.lower()
    if suffix not in {".css", ".html"}:
        return set()
    content = source.read_text(encoding="utf-8")
    if suffix == ".css":
        return {match.group(2) for match in CSS_URL.finditer(content)}
    if suffix == ".html":
        parser = LocalReferences()
        parser.feed(content)
        return parser.references
    return set()


def publish_report_html(source: Path, destination: Path) -> None:
    html = source.read_text(encoding="utf-8")
    if OSM_TILE_URL in html and OSM_NO_REFERRER in html:
        # OSM requires a Referer from web pages. Keep the report path private.
        html = OSM_NO_REFERRER_NOTE.sub(
            lambda match: (
                f"{match.group('indent')}/* Send this site's origin to OpenStreetMap. */\n"
                f"{match.group('indent')}"
            ),
            html,
        )
        html = html.replace(OSM_NO_REFERRER, OSM_SITE_REFERRER)
    destination.write_text(html, encoding="utf-8")


def copy_with_dependencies(source: Path, folder: Path, copied: set[Path]) -> None:
    source = source.resolve()
    folder = folder.resolve()
    if not source.is_relative_to(folder) or not source.is_file():
        raise ValueError(f"Invalid report asset: {source}")
    if source in copied:
        return
    copied.add(source)
    destination = OUTPUT / "reports" / folder.name / source.relative_to(folder)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".html":
        publish_report_html(source, destination)
    else:
        shutil.copy2(source, destination)

    for reference in references_in(source):
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        asset = (source.parent / unquote(parsed.path)).resolve()
        if not asset.is_relative_to(folder):
            raise ValueError(f"Asset escapes report folder: {reference} in {source}")
        if not asset.is_file():
            raise FileNotFoundError(f"Missing report asset: {reference} in {source}")
        copy_with_dependencies(asset, folder, copied)


def describe(folder: Path, report: Path, photos: dict[str, dict[str, str]]) -> dict:
    match = STAMP.search(folder.name)
    raw_title = folder.name[: match.start()] if match else folder.name
    fallback_title = re.sub(r"\s+", " ", raw_title.replace("_", " ").replace("-", " ")).strip()
    title = report_heading(report) or fallback_title
    session_match = re.search(r"#\d+$", folder.name)
    session = f"Session {session_match.group()}" if session_match else "Session report"
    date_label = time_label = sort_date = ""
    if match:
        recorded = datetime.strptime(
            f"{match.group('date')}_{match.group('time')}", "%Y-%m-%d_%H-%M-%S"
        )
        date_label = f"{recorded.day} {recorded.strftime('%b %Y')}"
        time_label = recorded.strftime("%I:%M %p").lstrip("0").lower()
        sort_date = recorded.isoformat()

    return {
        "id": folder.name,
        "title": title or "Bird recording",
        "session": session,
        "dateLabel": date_label,
        "timeLabel": time_label,
        "sortDate": sort_date,
        "url": f"reports/{quote(folder.name, safe='')}/{quote(report.name, safe='')}",
        "leadingBird": leading_bird(report, photos),
    }


def build() -> None:
    photos = json.loads(PHOTO_CATALOGUE.read_text(encoding="utf-8"))
    for photo in photos.values():
        image = SOURCE / photo["image"]
        if not image.is_file() or not image.resolve().is_relative_to(SOURCE.resolve()):
            raise ValueError(f"Missing or invalid bird photo: {photo['image']}")

    if OUTPUT.exists():
        if OUTPUT.is_symlink() or OUTPUT.resolve().parent != ROOT.resolve():
            raise ValueError("Refusing to replace an unexpected output directory")
        shutil.rmtree(OUTPUT)
    shutil.copytree(SOURCE, OUTPUT)

    reports = []
    for folder in sorted(ROOT.iterdir()):
        if not folder.is_dir() or folder.name.startswith(".") or folder.name in SKIP_FOLDERS:
            continue
        html_files = sorted(folder.glob("*.html"))
        if len(html_files) != 1:
            raise ValueError(f"Expected one HTML report in {folder}, found {len(html_files)}")
        report = html_files[0]
        copy_with_dependencies(report, folder, set())
        reports.append(describe(folder, report, photos))

    (OUTPUT / "reports.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(reports)} report(s) in {OUTPUT}")


if __name__ == "__main__":
    build()
