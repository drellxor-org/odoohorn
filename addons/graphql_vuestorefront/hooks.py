"""Post-install / post-update hooks for graphql_vuestorefront.

Provisions:
  * the `pg_trgm` extension (used for fuzzy substring matching)
  * the `search_corpus` materialized view that backs the GraphQL `search` /
    `searchSuggest` queries — a flat denormalized table holding one row per
    searchable record (product / brochure / article) with a single `full_text`
    blob and a `make` column.
  * a unique index on (source, id) so REFRESH MATERIALIZED VIEW CONCURRENTLY works
  * a GIN trigram index on full_text so substring + word_similarity searches are fast

All statements are idempotent — safe to re-run on every -u graphql_vuestorefront.
"""

import logging

_logger = logging.getLogger(__name__)


SEARCH_CORPUS_SQL = r"""
DROP MATERIALIZED VIEW IF EXISTS search_corpus;

CREATE MATERIALIZED VIEW search_corpus AS
-- PRODUCTS --------------------------------------------------------------------
SELECT
    'PRODUCT'::text AS source,
    pt.id           AS id,
    pt.name->>'en_US' AS name,
    pm.name         AS make,
    pt.website_slug->>'en_US' AS slug,
    btrim(
        coalesce(pt.name->>'en_US', '')        || ' ' ||
        coalesce(pt.default_code, '')          || ' ' ||
        coalesce(pm.name, '')                  || ' ' ||
        coalesce(pm.code, '')                  || ' ' ||
        coalesce(cats.full_categ_path, '')
    ) AS full_text
  FROM product_template pt
  LEFT JOIN product_make pm ON pm.id = pt.make_id
  LEFT JOIN LATERAL (
      SELECT string_agg(ppc.name->>'en_US', ' / ' ORDER BY ppc.parent_path) AS full_categ_path
        FROM product_public_category_product_template_rel rel
        JOIN product_public_category ppc ON ppc.id = rel.product_public_category_id
       WHERE rel.product_template_id = pt.id
  ) cats ON TRUE
 WHERE pt.active = TRUE

UNION ALL
-- BROCHURES ------------------------------------------------------------------
SELECT
    'BROCHURE'::text AS source,
    b.id            AS id,
    b.name->>'en_US' AS name,
    roots.root_names AS make,
    b.website_slug->>'en_US' AS slug,
    btrim(
        coalesce(b.name->>'en_US', '')         || ' ' ||
        coalesce(cats.full_categ_path, '')
    ) AS full_text
  FROM brochure b
  LEFT JOIN LATERAL (
      SELECT string_agg(bc.name->>'en_US', ' / ' ORDER BY bc.parent_path) AS full_categ_path
        FROM brochure_brochure_category_rel rel
        JOIN brochure_category bc ON bc.id = rel.category_id
       WHERE rel.brochure_id = b.id
  ) cats ON TRUE
  LEFT JOIN LATERAL (
      -- root-level category name(s) = the brochure-side "make"
      SELECT string_agg(DISTINCT root_bc.name->>'en_US', ' ') AS root_names
        FROM brochure_brochure_category_rel rel
        JOIN brochure_category bc ON bc.id = rel.category_id
        JOIN brochure_category root_bc
             ON root_bc.id = split_part(bc.parent_path, '/', 1)::int
       WHERE rel.brochure_id = b.id
  ) roots ON TRUE
 WHERE b.active = TRUE

UNION ALL
-- ARTICLES -------------------------------------------------------------------
SELECT
    'ARTICLE'::text AS source,
    a.id            AS id,
    a.name->>'en_US' AS name,
    NULL::text      AS make,
    a.website_slug  AS slug,
    btrim(
        coalesce(a.name->>'en_US', '') || ' ' || coalesce(a.body->>'en_US', '')
    ) AS full_text
  FROM article a
;

-- Unique index — required by REFRESH MATERIALIZED VIEW CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS ix_search_corpus_pk
    ON search_corpus (source, id);

-- Trigram GIN — accelerates both ILIKE '%...%' and word_similarity(...).
CREATE INDEX IF NOT EXISTS ix_search_corpus_full_text_trgm
    ON search_corpus USING gin (full_text gin_trgm_ops);

-- Plain make filter (rarely null for products, often null for articles).
CREATE INDEX IF NOT EXISTS ix_search_corpus_make
    ON search_corpus (make)
 WHERE make IS NOT NULL;
"""


def _ensure_pg_trgm(cr):
    cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def _ensure_search_corpus(cr):
    cr.execute(SEARCH_CORPUS_SQL)
    _logger.info('[search] search_corpus materialized view (re)created')


def post_init(cr, registry):
    _ensure_pg_trgm(cr)
    try:
        _ensure_search_corpus(cr)
    except Exception as e:
        _logger.warning('[search] could not build search_corpus during install: %s', e)
        cr.rollback()
