# Birdsong Archive

A public GitHub Pages catalogue for BirdNET Live session reports. The site lists each report folder at the repository root. Selecting one opens its HTML report in a viewer with a link to the full page. Each session has a short, stable URL and a Comentario discussion beneath the report. The About page at `/about/` introduces the archive and has its own general comment thread.

The Contact link opens the archive's `/contact/` page. Its form sends `name`, `email`, and `message` to the existing Google Apps Script web app used by the blog contact page, so GitHub Pages does not host a mail service. The blog contact page remains linked as an alternative. The form only reports success when the script returns readable JSON with `status: "ok"`; if the cross-origin response cannot be read, it reports delivery as unconfirmed and does not retry automatically.

## Add a recording

1. Add a folder at the repository root containing exactly one `.html` report.
2. Keep any audio, images, styles, or other files referenced by that report in the same folder or its subfolders. Use relative links in the HTML. Names with `#` are supported when encoded as `%23` in those links.
3. Commit and push the folder to `main`. The GitHub Actions workflow rebuilds the catalogue and publishes the site automatically.

From each report folder, only the HTML report and local files it references are copied into the public site. Metadata and selection text files are ignored by Git, so they remain local unless you explicitly choose to add them. Review the HTML and audio before pushing: repository files themselves are public too.

The home page photo in `site/images/magpie-samcem05.jpg` is by [Aviceda](https://commons.wikimedia.org/wiki/File:Magpie_samcem05.jpg), licensed [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The original file is preserved; the page crops it for display with CSS. Keep the footer credit and licence link if reusing the photo.

The About page uses an existing rainbow lorikeet photo from `site/images/`, with its source, author, licence, and crop notice in the caption.

Each session tile shows the highest-certainty species in the report's Confidence list **that has a usable catalogued photo**. If scores tie, the report's displayed order breaks the tie. The image and its photographer, source, and licence come from `scripts/bird_photos.json`. The small info button reveals the selected bird's name, confidence, count, and credit; it works with a mouse, keyboard, or tap. Images are cropped for display with CSS.

Species ranked above the selected bird but missing a usable photo are recorded in `reports.json` under `leadingBird.missingPhotos` and listed as warnings in the GitHub Actions build log. This provides a queue for future photos while the new session still publishes. If no species in the report has a usable photo, its tile uses the bird icon and a "Photo not yet available" note. To add a species photo, choose a reusable image, place a web-sized copy under `site/images/`, then add its scientific name and attribution details to the JSON catalogue. The source and licence links appear in the tile's info panel.

## Session links and comments

Session links use `/s/<short-id>/`. The ID is the first 12 hexadecimal characters of the SHA-256 hash of the source folder name, so adding more folders does not renumber existing sessions. The build rejects a collision. Keep a published folder name unchanged to preserve its session URL and comment thread. Older `/?report=<folder-name>` links redirect to the corresponding short URL.

The viewer loads the light Comentario widget from `https://comments.neilennis.com/comentario.js` beneath the report. The About page loads the same widget for a separate conversation. Comentario uses each page's URL path to separate discussions and link notification emails back to the right page. Register `birds.neilennis.com` as a domain in Comentario. The raw "Open full page" report is for reading the source report separately; comments live on the session page. Local previews show a note instead of connecting to Comentario, because the local host is not registered there.

## Publish on GitHub Pages

The repository's **Settings → Pages** uses **GitHub Actions** as the publishing source. Push to `main`, then watch the **Publish Birdsong Archive** workflow under **Actions**. The public address is **https://birds.neilennis.com/**.

The custom domain is set in GitHub Pages settings. Cloudflare DNS has a **DNS only** CNAME record named `birds` pointing to `neil-ennis.github.io` (without `/birds`). Because this site is published by a custom Actions workflow, GitHub does not require a `CNAME` file in the repository. GitHub Pages manages the site's HTTPS certificate.

## Preview locally

Run `python scripts/build_site.py` from the repository root, then serve the generated `dist` folder with a local HTTP server, for example `python -m http.server 8000 --directory dist`. Open `http://localhost:8000/`. The generated `dist` folder is ignored by Git.

The build fails if a report folder has zero or multiple top-level HTML files, or if a report references a missing local file. This keeps incomplete reports from silently appearing on the public site.

BirdNET Live reports may request OpenStreetMap tiles with `referrerPolicy: 'no-referrer'`, which OpenStreetMap blocks on websites. During the build, the published HTML copies use `strict-origin-when-cross-origin` for those tiles. The source reports stay unchanged, and the map sends the site origin without exposing the report path.
