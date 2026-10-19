import os
import tempfile
import zipfile


from odoo.tests import TransactionCase, tagged


CATALOG_HEADER = ('make,make_description,reference,make_reference,description_en,description_fr,'
                  'description_es,description_nl,description_it,description_de,dangerous_goods,'
                  'weight_gr,length_mm,height_mm,width_mm,family_en,subfamily_en,sub_subfamily_en,'
                  'family_fr,subfamily_fr,sub_subfamily_fr,family_es,subfamily_es,sub_subfamily_es,'
                  'family_nl,subfamily_nl,sub_subfamily_nl,family_it,subfamily_it,sub_subfamily_it,'
                  'family_de,subfamily_de,sub_subfamily_de')


def catalog_row(ref, desc):
    return (f'T99,TESTMAKE,{ref},T99/{ref},{desc},{desc} FR,,,,,FALSE,500,1,2,3,'
            'Test Family,Test Sub,,Famille,Sous,' + ',' * 11)


@tagged('post_install', '-at_install')
class TestTvhImport(TransactionCase):

    def setUp(self):
        super().setUp()
        self.dir = tempfile.mkdtemp()
        self.importer = self.env['tvh.import']
        self.Tmpl = self.env['product.template'].with_context(active_test=False)

    def write(self, name, lines):
        path = os.path.join(self.dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        return path

    def product(self, ref):
        return self.Tmpl.search([('default_code', '=', ref), ('make_id.code', '=', 'T99')])

    def import_catalog(self, *rows):
        self.importer._import_catalog(self.write('c.csv', [CATALOG_HEADER, *rows]))

    def test_catalog_delta(self):
        self.import_catalog(catalog_row('A1', 'PUMP'), catalog_row('A2', 'VALVE'))
        a1, a2 = self.product('A1'), self.product('A2')
        self.assertEqual(a1.name, 'PUMP')
        self.assertEqual(a1.with_context(lang='fr_FR').name, 'PUMP FR')
        self.assertEqual(a1.weight, 0.5)
        self.assertEqual(a1.public_categ_ids.name, 'Test Sub')
        self.assertEqual(a1.public_categ_ids.parent_id.name, 'Test Family')
        self.assertEqual(a1.website_slug, '/parts/testmake/a1-pump')
        self.assertEqual(a1.with_context(lang='fr_FR').website_slug, a1.website_slug, 'one slug for every language')
        self.env.flush_all()
        self.env.cr.execute('SELECT website_slug FROM product_template WHERE id = %s', [a1.id])
        self.assertEqual(list(self.env.cr.fetchone()[0]), ['en_US'], 'slug stored under en_US only')

        self.import_catalog(catalog_row('A1', 'BIG PUMP'))
        self.assertEqual(a1.name, 'BIG PUMP')
        self.assertEqual(a1.website_slug, '/parts/testmake/a1-pump', 'a public url never follows renames')
        self.assertFalse(a2.active, 'dropped from the file → archived')

        # inquiry stubs (no digest) are never archived
        stub = self.Tmpl.create({'name': 'stub', 'default_code': 'S1', 'make_id': a1.make_id.id})
        self.import_catalog(catalog_row('A1', 'BIG PUMP'))
        self.assertTrue(stub.active)

    def test_applications_keep_manual_brochure(self):
        self.import_catalog(catalog_row('A1', 'PUMP'))
        header = 'Make,Reference,Vehicle_Type_Code,Vehicle_Brand,model,serie,Engine_Brand,Engine_Series,Engine_Model'
        path = self.write('a.csv', [header, 'T99,A1,32,MANITOU,MLT 733,,DEUTZ,,TCD 3.6',
                                    'T99,A1,32,MANITOU,MT 1340,,PERKINS,,854E'])
        self.importer._import_applications(path)
        apps = self.product('A1').application_ids
        self.assertEqual(len(apps), 2)

        brochure = self.env['brochure'].create({'name': 'hand picked'})
        apps.filtered(lambda a: a.model == 'MLT 733').brochure_id = brochure
        path = self.write('a.csv', [header, 'T99,A1,32,MANITOU,MLT 733,,DEUTZ,,TCD 3.6 L'])
        self.importer._import_applications(path)
        apps = self.product('A1').application_ids
        self.assertEqual(apps.mapped('engine_model'), ['TCD 3.6 L'])
        self.assertEqual(apps.brochure_id, brochure, 'manual brochure survives a changed row')

    def test_stock_and_prices(self):
        self.import_catalog(catalog_row('A1', 'PUMP'))
        self.importer._import_stock(self.write('s.csv', ['make;reference;stock_UK;stock_BE',
                                                         'T99;A1;0;+10']))
        a1 = self.product('A1')
        self.assertEqual((a1.tvh_quantity_in_stock, a1.tvh_quantity_in_stock_be), ('NO', '+10'))

        path = os.path.join(self.dir, 'p.xlsx')
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('xl/sharedStrings.xml',
                       f'<sst {ns}><si><t>Make</t></si><si><t>Partno</t></si>'
                       f'<si><t>Sales Price 1 GBP</t></si><si><t>T99</t></si><si><t>A1</t></si></sst>')
            z.writestr('xl/worksheets/sheet1.xml',
                       f'<worksheet {ns}><sheetData>'
                       '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
                       '<c r="C1" t="s"><v>2</v></c></row>'
                       '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>4</v></c>'
                       '<c r="C2"><v>12.345</v></c></row></sheetData></worksheet>')
        self.importer._import_prices(path)
        self.assertEqual((a1.tvh_price, a1.list_price), (12.35, 12.35))

        a1.tvh_price = 11.0  # manual "Refresh from TVH"
        self.importer._import_prices(path)
        self.assertEqual(a1.tvh_price, 11.0, 'same file must not undo a manual refresh')
        self.assertEqual(a1.list_price, 11.0, 'shop price follows tvh_price')


@tagged('post_install', '-at_install')
class TestTvhInquiry(TransactionCase):

    def test_suggestions_link_only_known_parts(self):
        make = self.env['product.make'].create({'code': 'T98', 'name': 'TESTMAKE'})
        Tmpl = self.env['product.template']
        original = Tmpl.create({'name': 'PUMP', 'default_code': 'P1', 'make_id': make.id})
        known = Tmpl.create({'name': 'PUMP B', 'default_code': 'P2', 'make_id': make.id})
        line = lambda n, part, **kw: dict({'custLineNumber': n, 'lineNumber': int(float(n) * 10),
                                           'makeCode': 'T98', 'partNumber': part, 'price': 5.0}, **kw)
        count = Tmpl.search_count([])
        self.env['tvh.service']._apply_inquiry(original, {'lines': [
            line('1.0', 'P1'), line('1.1', 'P2'), line('1.2', 'UNKNOWN')]})
        self.assertEqual(original.alternative_product_ids, known)
        self.assertEqual(Tmpl.search_count([]), count, 'TVH suggestions must not create products')

        # replacement (priceCode 36) to a part we don't carry: not linked, nothing created
        self.env['tvh.service']._apply_inquiry(original, {'lines': [
            line('1.0', 'P1', priceCode='36'), line('1.1', 'UNKNOWN')]})
        self.assertFalse(original.replaced_by_id)
        self.assertEqual(Tmpl.search_count([]), count)
