# SEO tasks

From the SEO audit of 2026-10-12/13: front-end `develop` @ `c7c02ca`, odoohorn `tvh` @ `2a122ff`, staging `dev.silverhorn.co.uk`, local DB `odoo-test-45`.

Priority: **P0** loses indexing/traffic now · **P1** on-page quality · **P2** larger structural work.

Tasks marked 🔗 need a matching change on the other side; release them together.

## Status (2026-10-14)

Done on `tvh` (odoohorn) and `tvh` (front-end), not released yet:
- **P0 / final URL scheme:** FE-1 (homepage SSR), FE-3 (real 404s, 503 on outage), BE-URL / FE-URL (frozen readable slugs, routes, canonicals, breadcrumbs), BE-5 / FE-4 (legacy 301s incl. the 2023 sitemap urls), duplicate-model cleanup, sitemap, staging + PDF noindex. Deploy simulated on the July prod snapshot (main → tvh).
- **SEO brief (docx):** part page title/description/H1/breadcrumb/alt/og:image, clean head on client navigation, keywords dropped, hand-written SEO fields override the template (generated ones cleared), Product + BreadcrumbList JSON-LD.
- **Check:** `scripts/seo_check.py`. Full local run: 16,298 sitemap pages 200 + self canonical + indexable, 4,539/4,539 old urls one 301 to a live page, junk 404.

Open:
- **FE-5:** no `<h1>` on non-part pages (2,764: models, catalog hubs, articles, static pages).
- **Content:** duplicate hand-written titles/descriptions on ~50–60 model pages (copy-paste in Odoo SEO tabs).
- Release steps (push both branches, backend then frontend tag, sitemap resubmit), server `.env` lists (`seo_url`, `RECAPTCHA_PRIVATE_KEY`).
- P1/P2 below not listed above (FE-9 fitment table, FE-10 make hubs, FE-11 languages, BE-6, catalog import speed in simplify_odoo create()).

## Current prod state (crawl 2026-10-13)

Prod runs front-end `v0.0.4`; it has no parts catalog yet, only brochures. Crawl result: **from `/catalog`, crawlers can reach only 6 pages** (`/`, `/catalog`, `/articles`, `/about`, `/contact`, `/cart`), and none of them has an H1. Every page has `canonical=/`.

| Problem on prod | Cause | Fixed in `develop`? |
|---|---|---|
| Every content page (all 40 sampled sitemap URLs: brochures, categories, articles) renders as `<title>Silverhorn \| Loading...</title>`, no H1, no content | `v0.0.4` Apollo uses the relative uri `/graphql/vsf` under SSR → every server-side query fails with `NetworkError` (39 in 10 min in `silverhorn-ssr` logs) | ✅ `graphql.module.ts` prefixes `environment.apiUrl` on the server |
| Every page has `canonical = https://silverhorn.co.uk/`, so Google treats all of them as duplicates of the homepage | Hardcoded `<link rel="canonical">` in `src/index.html` | ✅ `SeoService.setCanonical` per route |
| `/catalog` links to no manufacturers or brochures | A consequence of the SSR data failure | ✅ with the GraphQL fix |
| `sitemap.xml` is a static file from 2023 (1,235 `/product/…` URLs = old brochures, 88 `/category/…`, 42 `/article/…`, all `lastmod` 2023-11-24) | `src/sitemap.xml` shipped as a build asset | ✅ proxied to Odoo's live sitemap |
| Homepage served as the static shell | `nginx.conf` `try_files $uri $uri/` | ❌ FE-1 |
| `/cart` indexable | no robots meta in `v0.0.4` | ✅ `noindex` |

**So the single most valuable SEO action is releasing `develop` to prod (new `v*` tag).** Release scope = every P0 task below. P1/P2 work continues after the release, and none of it may change a URL.

## P0 · Final URL scheme (decided 2026-10-14)

**Rule: every URL that reaches prod in this release is final.** Prod's current URLs (`/product/…`, `/category/…`, `/article/…-{id}`) change exactly once, at the release, each with one 301 (BE-5). After that, no URL changes as a side effect of editing data.

| Page | URL | Slug from | Unique by |
|---|---|---|---|
| Home / static | `/`, `/about`, `/contact` | — | — |
| Search, cart | `/search`, `/cart` (`noindex`) | — | — |
| Brochure catalog index | `/catalog` | — | — |
| Brochure category hubs | `/catalog/{make}[/{type}[/{series}]]`, e.g. `/catalog/yanmar/engines/3tnv70-engine-series` | category names | siblings (0 collisions) |
| Model (brochure) | `/model/{slug}`, e.g. `/model/yanmar-3tna72l-ubab` | brochure name (includes the make) | global; see collision rule |
| Diagram (future) | `/model/{model-slug}/{diagram-slug}`, e.g. `/model/yanmar-3tna72l-ubab/cylinder-head` | diagram name | within the model |
| Parts index / make hub | `/parts`, `/parts/{make}` (hub content later, URL reserved now) | make name | — |
| Part | `/parts/{make}/{part-no}-{name}`, e.g. `/parts/manitou/53015847-kit` | make + `default_code` + name | make + part no. (0 collisions) |
| Articles | `/articles`, `/article/{slug}`, e.g. `/article/new-yanmar-2tnv70-engine` | article name | global (0 collisions) |
| Languages (later, FE-11) | `/{lang}/…` prefix (`/de/catalog/…`), English at root | — | reserved now, so no first path segment may be a language code |

Rules:
- **Readable names, no raw ids.** Ids appear only as a last-resort collision suffix.
- **Slugs are stored and frozen at creation** (first publish). Renaming a record never changes its URL. A slug changes only by a deliberate edit of the slug field. Then a `write()` hook stores the old path in `legacy.url`, which 301s to the record. That hook is the only automatic redirect source.
- **Category hub paths** are the exception: they follow the tree, because the tree is editorial and gets reorganised. A rename or move of a category recomputes the hub paths below it, and the same hook writes `legacy.url` rows for the old paths. Models, diagrams, parts and articles are **not** nested under categories, so reorganising the tree never moves them.
- **Collision rule** at slug creation: if taken, append the primary category's leaf name (`-early-model`, `-excavators`); if still taken, append `-2`, `-3`… Enforced by a unique constraint per namespace (`/catalog` tree, `/model`, `/parts/{make}`, `/article`).
- **Breadcrumbs don't depend on the URL.** Model → its **primary category** trail (Yanmar › Engines › 3TNV70 series › model); part → Parts › make; article → Articles. Each brochure needs one stored primary category: 218 sit in several, 62 span makes. Other categories just list and link it. The same trail feeds `BreadcrumbList`.
- Lowercase, no trailing slash, `https://silverhorn.co.uk` only. Every variant (case, trailing slash, `/index.html`, `www`) gets one 301. Query strings never appear in a canonical.
- **PDF manuals are going away** (diagrams replace them). Send `X-Robots-Tag: noindex` on PDFs now, so removing them later loses nothing.

Data cleanup that must happen first, so each record gets its final slug once: `docs/brochure_duplicates.md` → Actions (3 merges, renames, 2 deletions, 20 "early model" suffixes).

### P0 tasks implementing the scheme
- **BE-URL** (backend):
  - [ ] Stored, frozen `website_slug` per the table, en_US-only (`translate=False`).
  - [ ] Unique constraint per namespace, plus the collision rule.
  - [ ] `primary_category_id` on `brochure`; a `make` on brochure if the name prefix isn't reliable (95% of names start with it).
  - [ ] `write()` hook → `legacy.url` on slug edit and on category rename/move.
  - [ ] Lookups by exact stored slug, then `legacy.url` (301), then 404.
  - [ ] `jsonLd`/breadcrumb data from the primary category.
  - [ ] Sitemap emits exactly these URLs.
  - [ ] Run the duplicate cleanup.
- **FE-URL** (frontend):
  - [ ] Routes `/catalog/**` (UrlMatcher, any depth), `/model/:slug[/:diagram]`, `/parts/:make`, `/parts/:make/:part`, `/article/:slug`.
  - [ ] Every internal link uses the backend `slug`.
  - [ ] Canonical = slug. 301 when the backend answers with a redirect target; 404 when it answers not found.
  - [ ] Express middleware for case / trailing-slash normalisation.
  - [ ] Drop `/brochure…`, `/brochure-category…`, `/product/:slug` and the numeric `/parts/:id` routes.

---

## Frontend (`front-end` repo)

### FE-1 · P0 · SSR the homepage
`/` and `/index.html` are served as the static Angular shell (`<title>Silverhorn | Loading...</title>`, empty `<app-root>`) on staging **and** prod.
Cause: `.docker/nginx.conf` → `location /` has `try_files $uri $uri/ @ssr;`, and `$uri/` resolves `/` to `index.html`.

- [ ] `location /` → `try_files $uri @ssr;`
- [ ] `location = /index.html` → `return 301 /;`

This config is what serves both environments (verified 2026-10-13):
- staging: openresty → `silverhorn-web` → `silverhorn-ssr`
- prod (`46.202.131.202`): host nginx `sites-enabled/silverhorn.co.uk.conf` proxies `location /` to `127.0.0.1:8001` = `silverhorn-web:v0.0.4`, whose `default.conf` is byte-identical to the repo file.

So the repo fix reaches prod on the next `v*` tag. Nothing to change on the prod host.

**Done when:** `curl -A Googlebot https://dev.silverhorn.co.uk/` returns the rendered homepage, with H1, description and canonical; the same on `silverhorn.co.uk` after the tag release.

### FE-2 · P0 · 🔗 Part pages work on their final URL
Today the backend sitemap emits `/parts/12-point-flange-bolt-4993` while the frontend parses a numeric id, so all 13.5k sitemap URLs render "Part not found" + `noindex`. Superseded by the P0 scheme: parts move to `/parts/{make}/{part-no}-{name}` (FE-URL / BE-URL). This task is the part-page side of it:

- [ ] Look up the part by its stored slug; canonical = slug; `/parts/:id` and old forms → 301 (BE-5 / `legacy.url`), not a second live URL.
- [ ] Catalog, search and similar-parts links use `product.slug`.

**Done when:** every part URL in `sitemap.xml` returns 200, `index, follow` and a self-canonical.

### FE-3 · P0 · Real 404s
Unknown routes redirect to `/` (`**` route) and render the homepage with status 200, `canonical=/` and `index`. "Part / Brochure / Article / Category not found" also return 200.

- [ ] `NotFoundComponent` for `**`, no redirect.
- [ ] All not-found states set `res.status(404)` through the `RESPONSE` token under SSR.

### FE-4 · P0 · 🔗 301s for legacy prod URLs
Prod's sitemap (likely indexed) has 1,235 `/product/<slug>-<id>` (old brochures), 88 `/category/...` and 42 `/article/<slug>-<id>` URLs. All of them move to the P0 scheme (`/model/…`, `/catalog/…`, `/article/<slug>`), and the brochure ids changed in the migration.

- [ ] Express middleware in `server.ts`, ahead of the Angular engine: load `{old_path: current_slug}` from BE-5's `/legacy-urls.json` at startup and refresh it every ~10 min. A hit → `res.redirect(301, target)`. ~3k entries in a plain object; no backend call per request, no render before the 301.
- [ ] Unmapped `/product/*` and `/category/*` → 404 (FE-3), not the homepage.
- Not an nginx `map`: it is static (a rename makes targets stale), needs a redeploy for every change, and prod has two nginx layers.

### FE-4b · superseded by FE-URL
Id-based resolution was replaced by stored, frozen, readable slugs (P0 URL scheme). Kept from it, now P2: 218 brochures sit in several categories, and breadcrumbs use `primary_category_id`.

### FE-5 · P1 · One H1 per page
`page-header.component.html` renders the title as a `<div>`. As a result `/parts`, `/catalog`, about, contact, articles, article, brochure, brochure-category and search have no H1.

- [ ] Render the page-header title as `<h1>`.
- [ ] The part page and cart already have their own H1: stop passing `title` to the page header there (or the page ends up with 2 H1s).
- [ ] Part page H1 = `{Part name} {Part no} for {Make}` (currently the name only).
- [ ] Part page breadcrumbs: the last crumb is the literal "Part page" (`partPage.title`). Replace it with `{Part name} {Part no}`, the same trail the `BreadcrumbList` uses.
- [ ] Homepage H1 "Find any part worldwide": add keywords, e.g. "Construction & material handling machinery parts".

### FE-6 · P1 · 🔗 Use backend SEO fields properly
Today `website_meta_title` only reaches `og:title`, and `website_meta_description` only reaches `og:description`. The Odoo fallback `og:image` (website logo 300×300 on the backend host) overwrites the article image.

- [ ] `SeoService.setMeta`: `meta_title` → `<title>` as-is (no prefix), `meta_description` → `<meta name="description">` (needs BE-1).
- [ ] Apply `og:image` from the backend only when it is present (BE-1 stops sending the logo).
- [ ] Part page: add `seoMetadata` to the `ProductById` query and call `setMeta` (it currently ignores all backend SEO).

### FE-7 · P1 · Titles, descriptions, images
- [ ] Put the brand last: `"{page} | SilverHorn"` (`seo.service.ts` `setTitle`).
- [ ] Fallback part title (when no backend meta): `{Part name} {Part no} for {Make} | SilverHorn`; same pattern as BE-2. Do not use the bare name: 13,023 of 13,534 products share a name ("O-RING" ×620).
- [ ] Part page `og:image`: `image` (1920) or `thumbnail` (512), not `smallImage` (128). Check the real pixel size: `image_1920` is only an upper bound, and a small TVH original stays small. Skip `og:image` when the image is under ~600 px wide rather than send a tiny one.
- [ ] Real part images: `alt` = `{Part name} {Part no} for {Make}`. This covers the main image (currently `alt=""`) and the thumbnails in the catalog, search and similar-parts lists. Purely decorative images (placeholder search icon, flags) keep `alt=""`.
- [ ] Default `og:image`: add a 1200×630 PNG to assets and set it in `SeoService.reset` (the TODO is already there).
- [ ] `SeoService.reset()` does not reset `og:title`, `og:image`, `twitter:image` or `keywords`. On client-side navigation, a page that sets none of them keeps the previous product's values. Reset all of them (default image, remove keywords).
- [ ] Acceptance: open a part URL directly (SSR) **and** navigate part → part → `/about` in the browser. Head has exactly one of each tag, nothing left over from the previous page; `og:title` = `<title>`, `og:description` = description, `og:url` = canonical.
- [ ] Brand spelling is **SilverHorn** (decided 2026-10-14). Change `SITE_NAME` in `seo.service.ts` from "Silverhorn" and use "SilverHorn" in titles, `og:site_name`, the `Organization` JSON-LD and the stored backend meta (BE-2/BE-3). The legal name in the footer stays "SilverHorn Ltd.".
- [ ] `/parts` is titled "Catalog" and `/catalog` is titled "Parts": swap or rename them, and give `/catalog` its own description.
- [ ] `/articles` title "Featured" → "Articles" / "News".
- [ ] Drop `meta keywords` (optional; Google ignores it).

### FE-8 · P1 · 🔗 Structured data (JSON-LD): render it
There is none on the site. Record-level JSON-LD comes from the backend again (BE-10); the frontend only injects it and adds the site-level blocks.

- [ ] Fetch `jsonLd` in the part, brochure, brochure-category and article queries. Inject it as `<script type="application/ld+json">` in `<head>` through `SeoService` (SSR; replace it on navigation, don't append).
- [ ] Homepage (static, frontend-owned): `Organization` (name, logo, phone, email, address) + `WebSite` with `SearchAction` (`/search?q={query}`).

**Done when:** Google Rich Results Test passes for one URL of each type.

### FE-9 · P1 · 🔗 Show machine compatibility on part pages
11,324 products have 536k application rows (make / model / engine). `Product.applications` is already in GraphQL, but none of it is rendered. This is the long-tail content ("o-ring manitou mt 1240").

- [ ] "Fits these machines" table on the part page (SSR-rendered, not lazy).
- [ ] Link rows to the brochure when `brochure_id` is set (needs BE-6).

### FE-10 · P2 · Indexable manufacturer / category pages
`/parts?make=1` canonicalises to `/parts`, and the filters are buttons, not links. No manufacturer or category landing page can rank, and `/parts` exposes only 10 product links.

- [ ] Make hubs at the reserved `/parts/{make}` URL (P0 scheme), with their own title, H1, intro text and crawlable `<a>` pagination. Machine-model landing pages belong to the brochure catalog (`/model/…`), not to `/parts`.
- [ ] Self-canonical on those pages; keep `?query` filter combinations canonical to their path.

### FE-11 · P2 · 🔗 Indexable languages
The language comes from the `frontend_lang` cookie on one URL, so Googlebot only sees English and fr/es/nl/it/de are invisible to search.

- [ ] Locale path prefix (`/de/...`) that sets the content language.
- [ ] `hreflang` alternates + `x-default` on every page; `<html lang>` per locale.

### FE-12 · P2 · Performance
- [ ] Load the Google Maps script only on `/contact` (it is currently synchronous on every page, in `index.html`).

---

## Backend (odoohorn)

### BE-1 · P1 · 🔗 Make `seoMetadata` carry the real fields
Odoo's `get_website_meta()` returns `meta_description: null` for these models and never exposes `website_meta_title` as a title. It also always fills `og:image` with the website logo from the backend host. This affects all `resolve_seo_metadata` resolvers: `schemas/objects.py` (category, product, article) and `schemas/brochure.py` (brochure, brochure category).

- [ ] Add `meta_title` = `website_meta_title`, and `meta_description` = `website_meta_description`.
- [ ] Send `og:image` / `twitter:image` only when `website_meta_og_img` is set.
- [ ] Drop `og:url` (it is the GraphQL endpoint; the frontend already ignores it).

One helper used by all five resolvers.

### BE-2 · P1 · Fix product meta auto-fill
`product_category_seo/models/product_template.py` uses the root `public_categ_ids` as the "manufacturer". TVH products keep the make in `make_id`, so stored titles read "Bearings TAPERED ROLLER BEARING ASSEMBLY". There are no part numbers, and only 1,654 distinct descriptions across 13.5k products.

- [ ] Title: `{Name (title case)} {default_code} – {make_id.name}`.
- [ ] Description (≤155 chars): name, make, part no., first 2–3 application models, delivery line.
- [ ] Hook it into the TVH import so new or renamed products get it.

### BE-3 · P1 · Regenerate existing meta values
`init_record_metadata` only fills **empty** fields, so the fixed templates don't reach existing records.

- [ ] One-off migration: clear and regenerate product meta title / description / keywords.
- [ ] Brochures: description = `description_sale` (1,004 have one) instead of "Order spares and service for X" (1,114 records).
- [ ] Articles: description = first ~155 chars of the body instead of "SilverHorn: Plant machinery spares…" (146 of 266).
- [ ] Decide first: these values are not flagged as hand-edited vs. generated, so the migration overwrites hand-edited ones too. Limit it to values that match the old templates.

### BE-4 · P1 · Social images
- [ ] Upload a 1200×630 social default image in Website settings (`has_social_default_image` is false).
- [ ] Optionally set `website_meta_og_img` for brochures/categories that have an image (0 records have one today).

### BE-5 · P0 · 🔗 Legacy URL redirect map
For FE-4: old prod `product.template` / `product.public.category` → new `brochure` / `brochure.category`.

Prod has **not** been migrated yet (checked 2026-10-13: `brochures` is not installed in `odoo-test-45`, which has 2,669 templates with `/product/...` slugs, more than the 1,235 in the static sitemap). The exact map exists only inside the migration: `brochures/hooks.py` builds `cat_map` / `brochure_map` (old id → new id, children → parent's brochure), then `_cleanup_legacy` deletes the source records and their slugs. Record the map there; do not reconstruct it later by name matching (names collide, ids changed).

- [ ] New model `legacy.url`: `path` (unique, indexed) + `res_model` + `res_id`. It stores the **target record**, not the target URL, so redirects follow later renames (BE-9). Several paths can point to one record (children, per-language slugs).
- [ ] In `migrate_data`, before `_cleanup_legacy`: write every distinct old `website_slug` value (all languages, plus `website_slug_override`) for migrated templates (parents and children) and public categories.
- [ ] Add rows for all 42 prod article URLs (`/article/<slug>-<id>` → the record; its new URL is `/article/<slug>`).
- [ ] Public endpoint `/legacy-urls.json` → `{path: record.website_slug}`, for published records only.
- [ ] Acceptance: run the migration on a copy of prod `odoo-test-45`. Every URL in prod's static sitemap, plus the Search Console "Pages" export, must give exactly one 301 hop to a 200 with a self-canonical. This is the go/no-go for the release.

### BE-9 · superseded by BE-URL
The problems listed here (renames breaking URLs, a category rename breaking every descendant, per-language slugs, unvalidated overrides) are all solved by BE-URL: frozen en_US slugs, unique constraints, and the `write()` hook into `legacy.url`. Still open, P1: product unpublished but `latest_product_id` set (TVH replacement chain) → 301 to the replacement's slug instead of 404.

### BE-10 · P1 · 🔗 Bring JSON-LD back to GraphQL
It was removed in `2cff17a`. Bring it back as a `jsonLd` field (a JSON string) on `Product`, `Brochure`, `BrochureCategory` and `Article`. **Do not restore the old builder as-is.** Besides exposing `list_price` (the TVH purchase price), it had these bugs:
- Offer URL built from `web.base.url` (the backend host) and `slug(self)` (wrong format).
- `availability` hardcoded to `InStock`.
- Image from `product.product/<template id>`.
- No brand.
- A stored `json_ld` value silently overrides everything.

Product (`Product`, **no `Offer`**). Decided 2026-10-14: the shown price is not a binding offer, because it can change between the quotation request and manual processing. Never emit `offers`, `price` or `availability`. Consequence: valid markup, but no Google product rich result and no free Shopping listings; we accept that. Revisit only if prices become firm.
- [ ] Add a test asserting the product JSON-LD contains no `offers` key, so it can't creep back in.
- [ ] `url` = `sitemap.website_url` param (`https://silverhorn.co.uk`) + `website_slug`, matching the canonical.
- [ ] `name` = `{Part name} {Part no} for {Make}`. `mpn` = `default_code`, the make's own part number (the TVH inquiry sends `makeCode` + `partNumber`). `sku` = our internal code (product id, or `tvh_number` once filled).
- [ ] `brand` = the **brand of the part itself**, not the machine make. TVH can supply aftermarket parts under an OEM number, so `brand: MANITOU` would claim a genuine part. Use `quality_brand` when set (7 products today). Use the make only when the part is confirmed genuine OEM, which needs a flag from TVH data. Otherwise omit `brand`.
- [ ] `category` and `weight` (`weight_gr`) when present.
- [ ] `image` = public `/web/image/product.template/<id>/image_1920` on the site domain.
- [ ] `description` = the generated meta description (BE-2).
- [ ] Optional: `isAccessoryOrSparePartFor` from `application_ids` (first N models).

Others:
- [ ] Every record type: `BreadcrumbList` (categories / make → record), with the same trail the page shows (FE-4b).
- [ ] Model (brochure): `CollectionPage` / `WebPage` about the model, not `Product`. Add an `ItemList` of parts once BE-6 / diagrams exist. No `DigitalDocument` for the PDFs: they are going away.
- [ ] Article: `Article` (`headline`, `image`, `datePublished` / `dateModified`, `author` = Organization).

Housekeeping:
- [ ] Drop the leftover `json_ld` columns, or turn them into an explicit manual override shown in the form view. Today they are invisible dead fields.

### BE-6 · P1 · 🔗 Link applications to brochures
Only 23 brochures are referenced by `product_application.brochure_id`, and brochure pages link to 0 parts.

- [ ] Fill in `brochure_id` on applications by matching make + model.
- [ ] Expose the brochure's compatible parts in the `Brochure` GraphQL type (paginated) so brochure pages can list and link them.

### BE-7 · P1 · Sitemap
`controllers/sitemap.py`:

- [ ] Add `/about`.
- [ ] Skip brochure categories with no brochures and no children (3 now, e.g. `toyota-92/reach-trucks-98`).
- [ ] Skip records whose page would 404 (unpublished, no slug).
- [ ] With FE-10/FE-11: add manufacturer pages and per-locale URLs (`xhtml:link hreflang`); switch to a sitemap index once over 50k URLs.

### BE-8 · P2 · 🔗 Translated slugs/meta per locale
Only after FE-11. Product meta is en_US-only (0 products have translated meta titles), and slugs are en_US by design (`d10ec1b`). Decide whether localized URLs keep the English slug (simplest) or get translated slugs.

---

## Infra

- [x] Staging `noindex` (done 2026-10-14). Lives **only on the staging server**, not in a repo: `/data/nginx/custom/server_proxy.conf` inside the `nginx-proxy-manager` container (195.110.58.122), `more_set_headers "X-Robots-Tag: noindex, nofollow";`. It applies to every NPM proxy host there (dev, dev-odoo, monitoring) and survives NPM regenerating its configs. Not in the repo `nginx.conf`: that file ships to prod too.
- [x] PDF manuals `X-Robots-Tag: noindex`: set by Odoo (`brochures/models/ir_http.py`), so it holds on both environments.
- [ ] `www.silverhorn.co.uk` has no DNS record and no server block on prod: add both, 301 to the apex domain.
- [ ] Prod still runs front-end `v0.0.4` (built 2026-06-23). Every frontend fix here needs a new `v*` tag to reach prod.

### Prod host hygiene (`46.202.131.202`; checked read-only 2026-10-13, nothing changed)
- [ ] **Security · SSH:** effective config is `PasswordAuthentication yes` and `PermitRootLogin yes`. Set `PasswordAuthentication no` in **both** `/etc/ssh/sshd_config:56` and `/etc/ssh/sshd_config.d/50-cloud-init.conf:1` (the drop-in overrides the main file), and `PermitRootLogin prohibit-password`. Then `sshd -t && systemctl reload sshd`, keeping the current session open while testing a new key login.
- [ ] Postgres 5432, Odoo 8069, cadvisor 8080 and node-exporter 9100 are published by Docker on `0.0.0.0`. They are closed from outside today, but Docker publishing bypasses `ufw`, so this relies on the provider firewall. Bind them to `127.0.0.1` (or drop the `ports:` entries) in the compose files.
- [ ] Remove the leftover `angular.silverhorn.co.uk` vhost (it only returns "OK") unless something health-checks it.
- [ ] `sites-enabled/default.conf` is actually the `odoo.silverhorn.co.uk` vhost, next to a separate `default`: rename it to `odoo.silverhorn.co.uk.conf` so it isn't mistaken for the default site.
- [ ] After FE-1…FE-4 ship: resubmit the sitemap in Search Console and watch Coverage for "Soft 404" / "Excluded by noindex".
