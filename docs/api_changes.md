# GraphQL API — what changed since the original VSF schema

All endpoints live under `POST /graphql/vsf` (auth: public, csrf disabled, cors `*`).
Sample requests are in [scripts/silverhorn-insomnia.json](../scripts/silverhorn-insomnia.json) (Insomnia v4 export).

---

## New queries

### `search(query, paging) → SearchResult`

Multi-entity search. Parses the input, runs a single SQL query against the
denormalized `search_corpus` materialized view, and returns three paginated slices.

```graphql
type ParsedQuery {
  make: String        # best-effort match against product.make or root brochure category
  model: String       # best fuzzy match against product.application.model, brochure category, or brochure name
  partNumber: String  # token resolving to a SKU (default_code) or a product-name substring
}

type SearchProductsSlice  { results: [Product!];  totalCount: Int!; hasMore: Boolean! }
type SearchBrochuresSlice { results: [Brochure!]; totalCount: Int!; hasMore: Boolean! }
type SearchArticlesSlice  { results: [Article!];  totalCount: Int!; hasMore: Boolean! }

type SearchResult {
  parsedQuery: ParsedQuery!
  products:  SearchProductsSlice!
  brochures: SearchBrochuresSlice!
  articles:  SearchArticlesSlice!
}

extend type Query {
  search(
    query: String!
    productsPage:   Int = 1, productsPageSize:   Int = 5
    brochuresPage:  Int = 1, brochuresPageSize:  Int = 5
    articlesPage:   Int = 1, articlesPageSize:   Int = 5
  ): SearchResult!
}
```

* Typo-tolerant via pg_trgm `word_similarity` (threshold 0.7 for model parsing, 0.4 for the corpus search).
* `make` is inferred from related data when not literally in the query (e.g., `4TNV98` → `Yanmar`).

### `searchSuggest(query, limit=8) → [Suggestion!]`

Type-ahead. Mixed top-N list across products/brochures/articles, ranked by
`word_similarity` against `search_corpus.full_text`.

```graphql
enum SuggestionType { PRODUCT BROCHURE ARTICLE }

type Suggestion {
  type: SuggestionType!
  id: Int!
  name: String!
  slug: String
  similarity: Float!
}

extend type Query {
  searchSuggest(query: String!, limit: Int = 8): [Suggestion!]!
}
```

### Brochure queries

```graphql
brochure(id: Int, slug: String): Brochure
brochures(search: String, categoryId: Int, categorySlug: String,
          pageSize: Int = 20, currentPage: Int = 1): BrochureList
brochureCategory(id: Int, slug: String): BrochureCategory
brochureCategories(parentId: Int, rootsOnly: Boolean = false): [BrochureCategory!]
```

Types: `Brochure`, `BrochureCategory`, `BrochureAttachment`, `BrochureList`.

---

## Existing query: `products` — new filter input + facets

```graphql
input FacetFilterInput {
  makeIds:         [Int]
  familyIds:       [Int]   # depth 0 of public_categ_ids
  subfamilyIds:    [Int]   # depth 1
  subsubfamilyIds: [Int]   # depth 2
}

input ProductFilterInput {
  # ...existing fields...
  facets: FacetFilterInput
}

type FacetValue { id: Int!; code: String; name: String; parentId: Int; count: Int! }

type ProductFacets {
  makes:          [FacetValue!]
  families:       [FacetValue!]
  subfamilies:    [FacetValue!]
  subsubfamilies: [FacetValue!]
}

extend type ProductList { facets: ProductFacets }
```

Faceting is **strict** — facet counts reflect the currently-filtered product set
(picking `subsubfamilyIds: [152]` excludes the sibling `153` from the facet list).

---

## `Product` type — new fields

```graphql
extend type Product {
  defaultCode: String
  qty: String                   # was Float — now from tvh_quantity_in_stock, "NO"/"1".."+10"

  # Catalog
  dataSource: DataSource
  make: ProductMake
  isDangerousGoods: Boolean
  weightGr: Float; lengthMm: Float; widthMm: Float; heightMm: Float
  applications: [ProductApplication!]

  # TVH
  tvhNumber: Int
  tvhPrice: Float; tvhListPrice: Float
  tvhQuantityInStock: String    # was Float
  tvhQuantityUpdatedAt: String
  qualityBrand: String
  unitCode: TvhUnitCode
  stockUnitMatrixDesc: String
  availabilityCode: TvhAvailabilityCode
  isReconditioned: Boolean
  isNonReturnable: Boolean
  isNonCancellable: Boolean
  surchargeAmount: Float
  environmentalFee: Float
  minimumOrderQuantity: Float
  orderable: Boolean
  notOrderableReason: String
  tvhQuantityDiscounts: [ProductTvhQuantityDiscount!]

  # Replacement chain
  replacedBy: Product
  latestProduct: Product
}

type DataSource             { id: Int!; code: String; name: String }
type ProductMake            { id: Int!; code: String; name: String; dataSource: DataSource }
type TvhAvailabilityCode    { id: Int!; code: String; description: String }
type TvhUnitCode            { id: Int!; code: String; description: String; isoCode: String }
type ProductTvhQuantityDiscount { id: Int!; qty: Float; price: Float }
type ProductApplication {
  id: Int!
  make: ProductMake
  model: String; serie: String
  vehicleTypeCode: String
  brochureId: Int; brochureName: String; brochureSlug: String
}
```

---

## `Order` type — brochure lines

```graphql
extend type Order {
  brochureLines: [OrderBrochureLine!]
}

type OrderBrochureLine {
  id: Int!
  name: String
  machineSerial: String
  partNumber: String
  commentary: String
  brochureId: Int
  brochureName: String
  brochureSlug: String
}
```

---

## Cart mutations — behavior changes

* `cart` no longer auto-creates a draft order. Returns `null` when no cart exists; the
  first `cartAddItem` / `cartAddBrochureItem` call creates it.
* `cartAddItem(productId, quantity)` — `productId` is now a **product.template id**;
  the variant is resolved server-side. Removed: `machineSerial`, `partNumber`, `commentary`.
* `cartUpdateItem(lineId, quantity)` — same simplification; just a quantity setter now.
* `cartAddMultipleItems` / `cartUpdateMultipleItems` / `cartRemoveMultipleItems` — same
  simplification (no per-line machine/part/commentary).

### New: brochure-line mutations

```graphql
cartAddBrochureItem(brochureId: Int!,
                    machineSerial: String,
                    partNumber: String,
                    commentary: String): CartData
cartRemoveBrochureItem(lineId: Int!): CartData
```

`machineSerial`/`partNumber`/`commentary` describe the brochure-line context and are
stored on `sale.order.brochure.line`.

### `confirmOrder` — partner accepted inline, state goes to "sent"

```graphql
confirmOrder(name: String, email: String, phone: String, comment: String): { done: Boolean }
```

* If the cart's `partner_id` is still the public user, `name`+`email` are required
  and a partner is created/updated on the fly.
* On success, the order moves to **`sent`** (Quotation Sent) instead of `sale`
  (Sales Order). The customer-confirmation email + the company-notification email
  are still sent (via `order_product_info._send_order_confirmation_mail`).

---

## Internals worth knowing

* Search corpus is a Postgres materialized view (`search_corpus`) with a unique
  `(source, id)` index and a GIN trigram index on `full_text`. A cron
  (`Search: refresh corpus if dirty`) runs every 10 min; it only does
  `REFRESH MATERIALIZED VIEW CONCURRENTLY` when the dirty flag (set by writes on
  product / make / category / brochure / brochure_category / article) is set.
* `pg_trgm` extension is provisioned by the `graphql_vuestorefront` install/update
  hook.
* `pg_trgm.word_similarity` is used everywhere instead of plain `similarity` —
  catches a short query inside a long string (e.g. "4TNV98" inside an article body).

---

## Quick start in Insomnia

1. Import [scripts/silverhorn-insomnia.json](../scripts/silverhorn-insomnia.json).
2. Set the **Local Dev** env's `base_url` if your instance isn't on `http://localhost:8069`.
3. Replace placeholder ids (`1` in variable JSON) with real ones from your DB.
4. All bodies are `application/graphql` mime — Insomnia renders Query + Variables editors.
