"""Search engine — query parsing + multi-entity search/suggest backed by a
denormalized materialized view (`search_corpus`).

Layout:
  * search_corpus is one row per searchable record (product / brochure / article)
    with a single `full_text` blob and a `make` column (see hooks.SEARCH_CORPUS_SQL).
  * A "dirty" flag (ir.config_parameter) is set whenever a model that feeds the
    view is mutated. A cron checks the flag every 10 minutes and refreshes the
    view if it's true.
  * Search code queries the view once per call, then bulk-loads the matched
    records by (source, id) so the GraphQL types resolve cleanly.
"""

import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)


PART_NUMBER_RE = re.compile(r'^[A-Z0-9][A-Z0-9./-]{3,}$', re.IGNORECASE)
SEARCH_CORPUS_DIRTY = 'search.corpus.dirty'

# Lower threshold = more forgiving on typos. 0.4 reliably catches "msnitou" → "Manitou".
WORD_SIM_THRESHOLD = 0.4


def _tokens(text):
    return [t for t in re.findall(r"[\w./-]+", text or '') if t]


def _longest_match(tokens, by_lower):
    n = len(tokens)
    for size in range(n, 0, -1):
        for start in range(0, n - size + 1):
            joined = ' '.join(tokens[start:start + size]).lower()
            if joined in by_lower:
                return by_lower[joined], start, start + size
    return None


class SearchEngine(models.AbstractModel):
    _name = 'search.engine'
    _description = 'Catalog search engine (materialized view)'

    # ------------------------------------------------------------------
    #   Index / view provisioning + dirty-flag refresh
    # ------------------------------------------------------------------

    @api.model
    def _ensure_search_indexes(self):
        from ..hooks import _ensure_pg_trgm, _ensure_search_corpus
        _ensure_pg_trgm(self.env.cr)
        _ensure_search_corpus(self.env.cr)

    @api.model
    def mark_dirty(self):
        """Mark the search corpus as needing a refresh. Called from write hooks on
        the underlying models (see models/search_dirty.py).
        """
        self.env['ir.config_parameter'].sudo().set_param(SEARCH_CORPUS_DIRTY, '1')

    @api.model
    def refresh_if_dirty(self, force=False):
        """Cron entrypoint. REFRESH MATERIALIZED VIEW CONCURRENTLY if the dirty
        flag is set (or if `force=True`), then clear the flag.
        """
        param = self.env['ir.config_parameter'].sudo()
        if not force and param.get_param(SEARCH_CORPUS_DIRTY) != '1':
            return
        try:
            self.env.cr.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY search_corpus')
            param.set_param(SEARCH_CORPUS_DIRTY, '0')
            _logger.info('[search] search_corpus refreshed')
        except Exception as e:
            _logger.warning('[search] refresh failed: %s', e)
            self.env.cr.rollback()

    # ------------------------------------------------------------------
    #   Query parsing
    # ------------------------------------------------------------------

    @api.model
    def parse_query(self, text):
        """Extract best-effort facts from the search text:
          * make        — matched against product.make and root-level brochure.category
          * part_number — token that resolves to a SKU (default_code) or appears in a product name
          * model       — best fuzzy match against product.application.model
                          and brochure.category at depth >= 1
        """
        result = {'make': False, 'part_number': False, 'model': False}
        tokens = _tokens(text)
        if not tokens:
            return result

        used = set()

        # make: longest contiguous range matching a product.make.name OR a root brochure category.
        makes = self.env['product.make'].sudo().with_context(active_test=False).search([])
        make_by_name = {m.name.lower(): m.name for m in makes if m.name}
        root_cats = self.env['brochure.category'].sudo().with_context(active_test=False).search(
            [('parent_id', '=', False)])
        for c in root_cats:
            if c.name:
                make_by_name.setdefault(c.name.lower(), c.name)
        match = _longest_match(tokens, make_by_name)
        if match:
            make_name, s, e = match
            result['make'] = make_name
            for tok in tokens[s:e]:
                used.add(tok)

        # part_number: any candidate token that matches a real SKU or appears in a
        # product name. When we find one, also propagate the matched product's make
        # back into result['make'] (only if we didn't already extract one).
        Product = self.env['product.template'].sudo().with_context(active_test=False)
        for tok in tokens:
            if tok in used or not PART_NUMBER_RE.match(tok):
                continue
            hit = Product.search([('default_code', '=ilike', tok)], limit=1) \
                or Product.search([('name', 'ilike', tok)], limit=1)
            if hit:
                result['part_number'] = tok
                if not result['make'] and hit.make_id and hit.make_id.name:
                    result['make'] = hit.make_id.name
                used.add(tok)
                break

        # model: prefer ILIKE substring match. Fall back to fuzzy only when the
        # query is long enough (>=4 chars) that random trigram overlap is unlikely,
        # and only above a tight threshold (0.7).
        remaining = ' '.join(t for t in tokens if t not in used).strip()
        if remaining:
            like = '%' + remaining + '%'
            use_fuzzy = len(remaining) >= 4
            # Parameter order matches the placeholders below.
            # SELECT: word_similarity(remaining, value)  -> remaining
            # WHERE:  value ILIKE like                   -> like
            # WHERE:  word_similarity(remaining, value) > 0.7  -> remaining (if fuzzy)
            if use_fuzzy:
                fuzzy_clause = "OR word_similarity(%s, value) > 0.7"
                params = [remaining, like, remaining]
            else:
                fuzzy_clause = ""
                params = [remaining, like]
            self.env.cr.execute(f"""
                WITH model_candidates AS (
                    -- product.application.model
                    SELECT pa.model AS value, pm.name AS make_name
                      FROM product_application pa
                      LEFT JOIN product_make pm ON pm.id = pa.make_id
                     WHERE pa.model IS NOT NULL AND pa.model <> ''
                    UNION ALL
                    -- brochure.category at depth >= 1
                    SELECT bc.name->>'en_US' AS value,
                           root.name->>'en_US' AS make_name
                      FROM brochure_category bc
                      JOIN brochure_category root
                           ON root.id = split_part(bc.parent_path, '/', 1)::int
                     WHERE bc.parent_id IS NOT NULL
                       AND bc.name->>'en_US' IS NOT NULL
                       AND bc.name->>'en_US' <> ''
                    UNION ALL
                    -- brochure.name (parts-diagram titles often encode make+model)
                    SELECT b.name->>'en_US' AS value,
                           (SELECT r.name->>'en_US'
                              FROM brochure_brochure_category_rel rel
                              JOIN brochure_category bc2 ON bc2.id = rel.category_id
                              JOIN brochure_category r
                                   ON r.id = split_part(bc2.parent_path, '/', 1)::int
                             WHERE rel.brochure_id = b.id
                             LIMIT 1) AS make_name
                      FROM brochure b
                     WHERE b.active = TRUE
                       AND b.name->>'en_US' IS NOT NULL
                       AND b.name->>'en_US' <> ''
                )
                SELECT value, make_name,
                       word_similarity(%s, value) AS sim
                  FROM model_candidates
                 WHERE value ILIKE %s {fuzzy_clause}
                 ORDER BY sim DESC, length(value) ASC
                 LIMIT 1
            """, params)
            row = self.env.cr.fetchone()
            if row:
                result['model'] = row[0]
                if not result['make'] and row[1]:
                    result['make'] = row[1]
        return result

    # ------------------------------------------------------------------
    #   Search — runs against search_corpus
    # ------------------------------------------------------------------

    @api.model
    def _corpus_search(self, query, source=None, make=None, limit=5, offset=0):
        """Returns (rows, total) where rows is a list of dicts with
        keys: source, id, name, slug, sim.
        """
        q = (query or '').strip()
        if not q and not (source and make is None) and not make:
            # Nothing to filter on → empty result (we don't dump entire view).
            return [], 0

        where = []
        params = []
        if source:
            where.append('source = %s')
            params.append(source)
        if make:
            where.append('lower(coalesce(make, \'\')) = lower(%s)')
            params.append(make)
        if q:
            like = '%' + q + '%'
            where.append("(full_text ILIKE %s OR word_similarity(%s, full_text) > %s)")
            params.extend([like, q, WORD_SIM_THRESHOLD])

        if q:
            sim_expr = 'word_similarity(%s, full_text) AS sim'
            sim_params = [q]
        else:
            sim_expr = '1.0 AS sim'
            sim_params = []

        where_sql = ' AND '.join(where) if where else 'TRUE'

        sql = f"""
            SELECT source, id, name, slug, {sim_expr}
              FROM search_corpus
             WHERE {where_sql}
             ORDER BY sim DESC, id ASC
             LIMIT %s OFFSET %s
        """
        count_sql = f"SELECT COUNT(*) FROM search_corpus WHERE {where_sql}"

        self.env.cr.execute(sql, sim_params + params + [limit, offset])
        rows = [
            {'source': r[0], 'id': r[1], 'name': r[2] or '', 'slug': r[3], 'sim': float(r[4] or 0)}
            for r in self.env.cr.fetchall()
        ]
        self.env.cr.execute(count_sql, params)
        total = self.env.cr.fetchone()[0]
        return rows, total

    @api.model
    def search_products(self, query, page=1, page_size=5, make=None):
        offset = max(page - 1, 0) * page_size
        rows, total = self._corpus_search(query, source='PRODUCT', make=make,
                                          limit=page_size, offset=offset)
        ids = [r['id'] for r in rows]
        return self.env['product.template'].sudo().browse(ids), total

    @api.model
    def search_brochures(self, query, page=1, page_size=5, make=None):
        offset = max(page - 1, 0) * page_size
        rows, total = self._corpus_search(query, source='BROCHURE', make=make,
                                          limit=page_size, offset=offset)
        ids = [r['id'] for r in rows]
        return self.env['brochure'].sudo().browse(ids), total

    @api.model
    def search_articles(self, query, page=1, page_size=5):
        offset = max(page - 1, 0) * page_size
        rows, total = self._corpus_search(query, source='ARTICLE',
                                          limit=page_size, offset=offset)
        ids = [r['id'] for r in rows]
        return self.env['article'].sudo().browse(ids), total

    # ------------------------------------------------------------------
    #   Suggest — mixed top-N list, single query
    # ------------------------------------------------------------------

    @api.model
    def suggest(self, query, limit=8):
        q = (query or '').strip()
        if not q:
            return []
        like = '%' + q + '%'
        sql = """
            SELECT source, id, name, slug,
                   word_similarity(%s, full_text) AS sim
              FROM search_corpus
             WHERE full_text ILIKE %s OR word_similarity(%s, full_text) > %s
             ORDER BY sim DESC, id ASC
             LIMIT %s
        """
        self.env.cr.execute(sql, [q, like, q, WORD_SIM_THRESHOLD, limit])
        return [
            {'type': r[0], 'id': r[1], 'name': r[2] or '', 'slug': r[3],
             'similarity': float(r[4] or 0)}
            for r in self.env.cr.fetchall()
        ]
