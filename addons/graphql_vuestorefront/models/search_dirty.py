"""Write hooks that flag the search_corpus materialized view as needing a refresh.

Each model whose data lands in the view gets a tiny `_inherit` here; on any
create/write/unlink we set a single ir.config_parameter flag. The cron in
data/cron_data.xml (and the engine's refresh_if_dirty) picks it up.
"""

from odoo import api, models


def _mark(env):
    env['search.engine'].mark_dirty()


class _SearchDirtyMixin(models.AbstractModel):
    _name = 'search.dirty.mixin'
    _description = 'Marks search corpus dirty on writes'

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        _mark(self.env)
        return recs

    def write(self, vals):
        res = super().write(vals)
        _mark(self.env)
        return res

    def unlink(self):
        res = super().unlink()
        _mark(self.env)
        return res


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'search.dirty.mixin']


class ProductMake(models.Model):
    _name = 'product.make'
    _inherit = ['product.make', 'search.dirty.mixin']


class ProductPublicCategory(models.Model):
    _name = 'product.public.category'
    _inherit = ['product.public.category', 'search.dirty.mixin']


class Brochure(models.Model):
    _name = 'brochure'
    _inherit = ['brochure', 'search.dirty.mixin']


class BrochureCategory(models.Model):
    _name = 'brochure.category'
    _inherit = ['brochure.category', 'search.dirty.mixin']


class Article(models.Model):
    _name = 'article'
    _inherit = ['article', 'search.dirty.mixin']
