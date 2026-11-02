# Cloudflare Web Analytics

Analytics is intentionally disabled until a Cloudflare Web Analytics site token exists.

## One-time setup

1. In the Cloudflare dashboard, open **Analytics & Logs → Web Analytics**.
2. Add `sbusienei.github.io` as a site.
3. Copy the generated beacon snippet.
4. In `index.html`, replace the `CLOUDFLARE-ANALYTICS` comment with that snippet, immediately above `<script src="site.js"></script>`.

The site token is intended to be embedded publicly. Do not add a Cloudflare API token, account key, password, or other secret to this repository.

Cloudflare Web Analytics reports aggregate visits, referrers, pages, countries, and performance. It does not identify individual visitors.
