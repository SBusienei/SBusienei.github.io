# Portfolio automation

All automation is deterministic Python and GitHub Actions. It does not call an AI model or consume AI credits.

## Articles

`Sync articles` runs every Monday at 09:15 EAT and can also be run manually. It reads the public DEV API for `sbusienei` and the Medium RSS feed for `@sbusienei`, deduplicates cross-posts, downloads bounded local cover images, and updates `data/articles.json`.

Only entries listed in `data/featured-articles.json` become cards on the homepage. Each entry keeps a human-controlled URL, display title, and description. Add or remove an entry there to change the featured selection. Feed history alone never promotes an article.

Article changes are validated and committed directly to `main` only when synchronized content changed.

## Projects

`Propose project updates` runs every Monday at 09:30 EAT and can also be run manually. A repository is eligible only when all of these are true:

- owned by `SBusienei`
- public
- not a fork
- not archived
- has the `portfolio` repository topic

An eligible repository may include `portfolio.yml` at its root to override its card title, summary, proof points, categories, technologies, links, and image. When no image is configured, automation creates deterministic local SVG artwork.

Project changes are pushed to `automation/portfolio-projects` and opened or updated as an assigned pull request labeled `portfolio-update`. They never publish directly.

## Community

Use the **Community portfolio entry** issue form. Valid submissions update `data/community.yml` on a dedicated branch and open an assigned, labeled pull request. LinkedIn is not scraped, and merging the pull request remains the publishing decision.

## Failures and notifications

Failed scheduled or push workflows open or update an issue labeled `automation-failure` and assign it to `SBusienei`. GitHub sends email according to account notification settings. GitHub Mobile push notifications require notifications for **Assigned**, **Pull request review**, and repository Actions/issue activity to be enabled in the mobile app and GitHub notification settings.

Network calls use three bounded attempts. Validation failures prevent staging, commits, and pushes. Every workflow stages only named generated files and directories; none uses `git add .`.
