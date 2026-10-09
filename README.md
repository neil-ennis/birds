# Birdsong Archive

A public GitHub Pages catalogue for BirdNET Live session reports. The site lists each report folder at the repository root. Selecting one opens its HTML report in a viewer with a link to the full page.

## Add a recording

1. Add a folder at the repository root containing exactly one `.html` report.
2. Keep any audio, images, styles, or other files referenced by that report in the same folder or its subfolders. Use relative links in the HTML. Names with `#` are supported when encoded as `%23` in those links.
3. Commit and push the folder to `main`. The GitHub Actions workflow rebuilds the catalogue and publishes the site automatically.

Only the HTML report and local files it references are copied into the public site. Metadata and selection text files are ignored by Git, so they remain local unless you explicitly choose to add them. Review the HTML and audio before pushing: repository files themselves are public too.

## Publish on GitHub Pages

In the repository's **Settings → Pages**, set **Build and deployment → Source** to **GitHub Actions**. Push to `main`, then watch the **Publish Birdsong Archive** workflow under **Actions**. The site URL will be `https://neil-ennis.github.io/birds/` unless a custom domain is configured.

## Preview locally

Run `python scripts/build_site.py` from the repository root, then serve the generated `dist` folder with a local HTTP server, for example `python -m http.server 8000 --directory dist`. Open `http://localhost:8000/`. The generated `dist` folder is ignored by Git.

The build fails if a report folder has zero or multiple top-level HTML files, or if a report references a missing local file. This keeps incomplete reports from silently appearing on the public site.
