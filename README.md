# Bilal Aseel — professional portfolio

[Visit the website](https://bilalaseel.pages.dev/) · [العربية](https://bilalaseel.pages.dev/ar/) · [Svenska](https://bilalaseel.pages.dev/sv/)

A multilingual portfolio presenting my work in technical support, service operations, systems testing and IT teaching. It includes practical experience, technologies I work with and an honest account of my AI-assisted projects.

## My contribution

I defined the requirements, supplied and checked the professional content, reviewed the design and requested improvements. Implementation and deployment setup were AI-assisted. The project demonstrates that collaboration and review process; it is not a claim that I independently wrote every line of code.

## What is here

- **HTML:** semantic content and three complete language versions.
- **CSS:** responsive dark design, compact experience cards and Arabic right-to-left layout.
- **JavaScript:** keyboard-accessible skill tabs, product disclosures and language switching that keeps the current section.
- **Python:** standard-library tools that generate translations and check the public build.
- **GitHub Actions:** checks on changes, with publication to the existing Cloudflare Pages project when publishing access is configured.
- **Cloudflare Pages:** static hosting and managed HTTPS.

No framework or runtime backend is required for visitors. Google Fonts is loaded with system-font fallbacks. There is no contact form or analytics script in this project. Company and product names describe experience, not endorsement.

## Try it locally

Use Python 3.12 or newer and Node.js 22 for the syntax check:

```sh
python scripts/build_locales.py
python scripts/check_site.py
node --check dist/app.js
python -m http.server 4173 --bind 127.0.0.1 --directory site-build
```

Open `http://127.0.0.1:4173/`. Stop the preview with Ctrl+C.

## Make an update

1. Edit the English source in `dist/index.html`.
2. Update matching text in `locales/ar.json` and `locales/sv.json`. The generator rejects missing translations. `invariant-text.json` is reserved for shared proper names and technical labels.
3. Run the commands above. Review the three languages at desktop and mobile widths.
4. Commit the source and generated pages together. Review the change before merging to `main`.
5. GitHub Actions checks the site. When deployment is enabled, a successful change on `main` publishes to the existing site.

Detailed setup and recovery: [deployment guide](docs/DEPLOYMENT.md). Plain-language explanation: [English](docs/HOW_IT_WORKS.md) · [العربية](docs/HOW_IT_WORKS_AR.md).

## Public files and assets

`public-files.json` lists exactly what may be published. The build rejects extra files in `dist` and copies only approved files into `site-build`. CVs, applications, private operational information and credentials are excluded. The device-monitoring prototype described on the website is a separate project; its source is not included here.

Portraits are AI-edited images based on my own photographs. Product marks belong to their respective owners; see [asset sources](ASSETS.md). No blanket licence is granted for personal images or third-party trademarks.
