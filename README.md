# Birdsong Archive

A public GitHub Pages catalogue for BirdNET Live session reports. The site lists each report folder at the repository root. Selecting one opens its HTML report in a viewer with a link to the full page.

## Add a recording

1. Add a folder at the repository root containing exactly one `.html` report.
2. Keep any audio, images, styles, or other files referenced by that report in the same folder or its subfolders. Use relative links in the HTML. Names with `#` are supported when encoded as `%23` in those links.
3. Commit and push the folder to `main`. The GitHub Actions workflow rebuilds the catalogue and publishes the site automatically.

From each report folder, only the HTML report and local files it references are copied into the public site. Metadata and selection text files are ignored by Git, so they remain local unless you explicitly choose to add them. Review the HTML and audio before pushing: repository files themselves are public too.

The home page photo in `site/images/magpie-samcem05.jpg` is by [Aviceda](https://commons.wikimedia.org/wiki/File:Magpie_samcem05.jpg), licensed [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The original file is preserved; the page crops it for display with CSS. Keep the footer credit and licence link if reusing the photo.

## Publish on GitHub Pages

The repository's **Settings → Pages** uses **GitHub Actions** as the publishing source. Push to `main`, then watch the **Publish Birdsong Archive** workflow under **Actions**. The public address is **https://birds.neilennis.com/**.

The custom domain is set in GitHub Pages settings. Cloudflare DNS has a **DNS only** CNAME record named `birds` pointing to `neil-ennis.github.io` (without `/birds`). Because this site is published by a custom Actions workflow, GitHub does not require a `CNAME` file in the repository. GitHub Pages manages the site's HTTPS certificate.

## Preview locally

Run `python scripts/build_site.py` from the repository root, then serve the generated `dist` folder with a local HTTP server, for example `python -m http.server 8000 --directory dist`. Open `http://localhost:8000/`. The generated `dist` folder is ignored by Git.

The build fails if a report folder has zero or multiple top-level HTML files, or if a report references a missing local file. This keeps incomplete reports from silently appearing on the public site.

BirdNET Live reports may request OpenStreetMap tiles with `referrerPolicy: 'no-referrer'`, which OpenStreetMap blocks on websites. During the build, the published HTML copies use `strict-origin-when-cross-origin` for those tiles. The source reports stay unchanged, and the map sends the site origin without exposing the report path.
