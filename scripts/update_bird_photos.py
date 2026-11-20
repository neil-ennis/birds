"""Find photos for species selected in recording folders.

Run without arguments to review missing species and choose Commons photos.
Use --check for a local, read-only inventory without network requests.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from build_site import PHOTO_CATALOGUE, ROOT, SOURCE, read_species_selection


API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "BirdsongArchive/1.0 (personal static site photo catalogue)"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
LICENSE_NAME = re.compile(r"^(?:CC0|CC BY|CC BY-SA) \d\.\d$", re.IGNORECASE)
REQUIRED_CREDIT = ("image", "author", "sourceUrl", "license", "licenseUrl")


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def api_query(**params: str) -> dict:
    url = API + "?" + urlencode({"format": "json", "formatversion": "2", **params})
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
        data = json.load(response)
    if "error" in data:
        raise ValueError(f"Commons API: {data['error'].get('info', 'unknown error')}")
    return data


def selected_species() -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    for folder in sorted(ROOT.glob("BirdNET_Live_*")):
        if not folder.is_dir():
            continue
        # The build gives title-species.txt precedence when both files exist.
        for name in ("title-species.txt", "tile-species.txt"):
            path = folder / name
            species = read_species_selection(path)
            if species:
                result.setdefault(species, []).append(path)
                break
    return result


def catalogue_problem(entry: object) -> str | None:
    if not isinstance(entry, dict) or not all(entry.get(key) for key in REQUIRED_CREDIT):
        return "missing image or credit fields"
    image = (SOURCE / entry["image"]).resolve()
    if not image.is_relative_to(SOURCE.resolve()) or not image.is_file():
        return "image file is missing or outside the site folder"
    return None


@dataclass(frozen=True)
class Candidate:
    title: str
    page_url: str
    image_url: str
    mime: str
    author: str
    license_name: str
    license_url: str
    description: str


def metadata_value(info: dict, name: str) -> str:
    return str(info.get("extmetadata", {}).get(name, {}).get("value", ""))


def candidate_from_page(page: dict, species: str) -> Candidate | None:
    info = (page.get("imageinfo") or [{}])[0]
    title = page.get("title", "")
    description = plain_text(metadata_value(info, "ImageDescription"))
    if species.casefold() not in f"{title} {description}".casefold():
        return None
    mime = info.get("mime", "")
    author = plain_text(metadata_value(info, "Artist"))
    license_name = plain_text(metadata_value(info, "LicenseShortName"))
    license_url = metadata_value(info, "LicenseUrl").strip()
    image_url = info.get("thumburl") or info.get("url", "")
    page_url = info.get("descriptionurl", "")
    if (
        mime not in IMAGE_TYPES
        or not author
        or not LICENSE_NAME.fullmatch(license_name)
        or urlparse(license_url).hostname not in {"creativecommons.org", "www.creativecommons.org"}
        or urlparse(image_url).hostname not in {"upload.wikimedia.org", "thumb.wikimedia.org"}
        or urlparse(page_url).hostname != "commons.wikimedia.org"
    ):
        return None
    return Candidate(title, page_url, image_url, mime, author, license_name, license_url, description)


def find_candidates(species: str) -> list[Candidate]:
    matches = api_query(
        action="query", list="search", srsearch=species, srnamespace="6", srlimit="12", srprop=""
    ).get("query", {}).get("search", [])
    titles = [item["title"] for item in matches]
    if not titles:
        return []
    pages = api_query(
        action="query",
        prop="imageinfo",
        titles="|".join(titles),
        iiprop="url|size|mime|extmetadata",
        iiurlwidth="1200",
        iiextmetadatafilter="Artist|LicenseShortName|LicenseUrl|ImageDescription",
        iiextmetadatalanguage="en",
    ).get("query", {}).get("pages", [])
    by_title = {page.get("title"): page for page in pages}
    candidates = [candidate_from_page(by_title.get(title, {}), species) for title in titles]
    return [candidate for candidate in candidates if candidate is not None][:5]


def image_bytes(candidate: Candidate) -> bytes:
    request = Request(candidate.image_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        if response.headers.get_content_type() != candidate.mime:
            raise ValueError("Downloaded image type differs from the Commons metadata")
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds the 10 MB download limit")
    signatures = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not signatures[candidate.mime]:
        raise ValueError("Downloaded file is not a valid image of the expected type")
    return data


def save_catalogue(catalogue: dict, expected_bytes: bytes) -> None:
    if PHOTO_CATALOGUE.read_bytes() != expected_bytes:
        raise RuntimeError("Photo catalogue changed during this run; please rerun the utility")
    newline = "\r\n" if b"\r\n" in expected_bytes else "\n"
    content = (json.dumps(catalogue, ensure_ascii=False, indent=2) + "\n").replace("\n", newline)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=PHOTO_CATALOGUE.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(content.encode("utf-8"))
        os.replace(temporary, PHOTO_CATALOGUE)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def add_photo(species: str, candidate: Candidate, catalogue: dict) -> None:
    filename = re.sub(r"[^a-z0-9]+", "-", species.casefold()).strip("-")
    destination = SOURCE / "images" / f"{filename}{IMAGE_TYPES[candidate.mime]}"
    if destination.exists():
        raise FileExistsError(f"Image path already exists: {destination}")
    data = image_bytes(candidate)
    original_catalogue = PHOTO_CATALOGUE.read_bytes()
    catalogue[species] = {
        "image": f"images/{destination.name}",
        "author": candidate.author,
        "sourceUrl": candidate.page_url,
        "license": candidate.license_name,
        "licenseUrl": candidate.license_url,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    image_created = False
    try:
        with destination.open("xb") as output:
            image_created = True
            output.write(data)
        save_catalogue(catalogue, original_catalogue)
    except Exception:
        if image_created:
            destination.unlink(missing_ok=True)
        catalogue.pop(species, None)
        raise
    print(f"Saved {destination} ({len(data):,} bytes) and updated {PHOTO_CATALOGUE}")


def run(check_only: bool) -> int:
    catalogue = json.loads(PHOTO_CATALOGUE.read_text(encoding="utf-8"))
    selections = selected_species()
    missing: list[str] = []
    problems = 0
    for species, paths in sorted(selections.items()):
        key = next((name for name in catalogue if name.casefold() == species.casefold()), None)
        if key is None:
            missing.append(species)
            state = "MISSING"
        else:
            problem = catalogue_problem(catalogue[key])
            state = f"REPAIR NEEDED: {problem}" if problem else "OK"
            problems += bool(problem)
        print(f"{state}: {species} ({', '.join(str(path.relative_to(ROOT)) for path in paths)})")
    print(f"Checked {len(selections)} selected species; {len(missing)} missing; {problems} need repair.")
    if check_only or not missing:
        return 1 if problems or (check_only and missing) else 0

    for species in missing:
        print(f"\nSearching Wikimedia Commons for {species}...")
        candidates = find_candidates(species)
        for number, item in enumerate(candidates, 1):
            print(f"{number}. {item.title} — {item.author} — {item.license_name}")
            print(f"   {item.page_url}")
            if item.description:
                print(f"   {item.description[:180]}")
        if not candidates:
            print("No suitable candidate found. Review Commons manually and leave this species for later.")
            continue
        choice = input("Choose a photo number, or press Enter to skip: ").strip()
        if not choice:
            continue
        if not choice.isdecimal() or not 1 <= int(choice) <= len(candidates):
            print("Invalid choice; skipped.")
            continue
        chosen = candidates[int(choice) - 1]
        if input(f"Save {chosen.title} for {species}? [y/N] ").strip().casefold() != "y":
            print("Skipped.")
            continue
        add_photo(species, chosen, catalogue)
    return 1 if problems or any(species not in catalogue for species in missing) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check selections locally without downloading")
    args = parser.parse_args()
    try:
        return run(args.check)
    except (OSError, ValueError, RuntimeError, EOFError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
