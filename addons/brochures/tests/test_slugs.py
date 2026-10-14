from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestBrochureSlugs(TransactionCase):

    def setUp(self):
        super().setUp()
        Cat = self.env['brochure.category']
        self.yanmar = Cat.create({'name': 'Yanmar Test'})
        self.engines = Cat.create({'name': 'Engines', 'parent_id': self.yanmar.id})
        self.series = Cat.create({'name': '3TNV70 Series', 'parent_id': self.engines.id})
        self.excavators = Cat.create({'name': 'Excavators', 'parent_id': self.yanmar.id})
        self.early = Cat.create({'name': 'Early Models', 'parent_id': self.yanmar.id})
        self.denyo = Cat.create({'name': 'Denyo Test'})
        self.denyo_engines = Cat.create({'name': 'Engines', 'parent_id': self.denyo.id})

    def brochure(self, name, *cats):
        return self.env['brochure'].create({'name': name, 'category_ids': [(6, 0, [c.id for c in cats])]})

    def test_category_paths_follow_the_tree(self):
        self.assertEqual(self.series.website_slug, '/catalog/yanmar-test/engines/3tnv70-series')
        self.assertEqual(self.denyo_engines.website_slug, '/catalog/denyo-test/engines')
        self.yanmar.name = 'Yanmar Renamed'
        self.assertEqual(self.series.website_slug, '/catalog/yanmar-renamed/engines/3tnv70-series')

    def test_primary_category_is_the_makes_deepest(self):
        b = self.brochure('Yanmar Test 3TNV70-FDW', self.denyo_engines, self.engines, self.series)
        self.assertEqual(b.primary_category_id, self.series)
        b.category_ids = [(3, self.series.id)]
        self.assertEqual(b.primary_category_id, self.engines, 'follows when the primary is removed')

    def test_model_slugs_are_readable_unique_and_frozen(self):
        early = self.brochure('Yanmar Test B03', self.early)
        excavator = self.brochure('Yanmar Test B03', self.excavators)
        third = self.brochure('Yanmar Test B03', self.excavators)
        self.assertEqual(early.website_slug, '/model/yanmar-test-b03')
        self.assertEqual(excavator.website_slug, '/model/yanmar-test-b03-excavators')
        self.assertEqual(third.website_slug, '/model/yanmar-test-b03-2')

        early.name = 'Yanmar Test B03 (early model)'
        self.assertEqual(early.website_slug, '/model/yanmar-test-b03', 'a public url never follows renames')
        self.assertFalse(early.copy().website_slug == early.website_slug)
