from odoo import fields, models, api
from odoo.addons.seo_url.models.slug_mixin import slugify

# Set once the old /article/{name}-{id} urls (and their overrides) have been
# moved to /article/{name} with redirects.
SLUGS_DONE_PARAM = 'article.final_slugs_done'


class Article(models.Model):
    _name = 'article'
    _description = 'Articles'
    _inherit = ['website.published.mixin', 'seo.slug.mixin']
    _order = "sequence, name"

    name = fields.Char('Title', required=True, translate=True)
    body = fields.Text('Body', required=True, translate=True)
    sequence = fields.Integer('Sequence')

    image_64 = fields.Image("Image 64", store=True, compute='_compute_image_1920')

    # Assigned once at creation by seo.slug.mixin; renames never change it.
    website_slug = fields.Char('Website slug', readonly=True, copy=False)
    article_images = fields.One2many('article.image', 'article_id', 'Article images')
    price = fields.Float('Price')
    availability = fields.Char('Availability')

    def _default_is_published(self):
        return True

    def _slug_candidates(self):
        return [f'/article/{slugify(self.name) or self.id}']

    @api.model
    def _init_slugs(self):
        """One-off: move every article from /article/{name}-{id} to /article/{name}.
        Prod serves both the computed slug and the hand-set override (83
        articles have one), so both become redirects. The override field is
        gone from the code; its column is still there. Runs on every update
        (data/slugs.xml), a no-op once done."""
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(SLUGS_DONE_PARAM):
            return
        cr = self.env.cr
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name = 'article' AND column_name = 'website_slug_override'")
        override = 'website_slug_override' if cr.fetchone() else 'NULL'
        cr.execute(f'SELECT id, website_slug, {override} FROM article')
        articles = self.with_context(active_test=False)
        for article_id, slug, old_override in cr.fetchall():
            self.env['legacy.url'].add([slug, old_override], articles.browse(article_id))
        articles.search([])._assign_slugs()
        params.set_param(SLUGS_DONE_PARAM, '1')

    @api.depends('article_images.sequence')
    def _compute_image_1920(self):
        for article in self:
            if article.article_images:
                top_image = min(article.article_images, key=lambda x: x.sequence)
                if top_image:
                    article.image_64 = top_image.image_64
            else:
                article.image_64 = False
