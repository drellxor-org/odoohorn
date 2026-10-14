from odoo import api, fields, models
from odoo.addons.seo_url.models.slug_mixin import ensure_slug_index, slugify


class BrochureCategory(models.Model):
    _name = 'brochure.category'
    _description = 'Brochure Category'
    _inherit = ['image.mixin', 'website.seo.metadata', 'website.published.mixin']
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    complete_name = fields.Char('Full Name', compute='_compute_complete_name', recursive=True, store=True)
    sequence = fields.Integer('Sequence', default=10)
    parent_id = fields.Many2one('brochure.category', 'Parent', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('brochure.category', 'parent_id', 'Children')

    page_message = fields.Text('Page Message', translate=True)

    # Hub urls follow the tree: it is editorial and gets reorganised. Models are
    # not nested under it, so moving a category never moves a model's url.
    website_slug = fields.Char('Website Slug', compute='_compute_website_slug', store=True, readonly=True,
                               translate=True, recursive=True, copy=False)
    json_ld = fields.Char('JSON-LD')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = f'{cat.parent_id.complete_name} / {cat.name}'
            else:
                cat.complete_name = cat.name

    def init(self):
        super().init()
        ensure_slug_index(self)

    @api.depends('name', 'parent_id.website_slug')
    def _compute_website_slug(self):
        # Stored under en_US only, like every other slug. Parents first: a parent
        # recomputed in the same batch isn't readable yet, so pass its slug down.
        computed = {}
        for cat in sorted(self.with_context(lang='en_US'), key=lambda c: (c.parent_path or '').count('/')):
            parent = computed.get(cat.parent_id.id) or (cat.parent_id.website_slug if cat.parent_id else '/catalog')
            leaf = slugify(cat.name) or str(cat.id)
            # Sibling names are unique today; number a duplicate (by age) rather
            # than fail the unique index.
            if isinstance(cat.id, int):
                siblings = cat.parent_id.child_id if cat.parent_id else self.search([('parent_id', '=', False)])
                older = siblings.filtered(lambda s: s.id < cat.id and slugify(s.name) == slugify(cat.name))
                if older:
                    leaf = f'{leaf}-{len(older) + 1}'
            computed[cat.id] = cat.website_slug = f'{parent}/{leaf}'

    def _default_is_published(self):
        return True
