from odoo.tests import TransactionCase, tagged

from ..models.product import _generated_title

MAKES = {'yanmar', 'denyo', 'none'}


@tagged('post_install', '-at_install')
class TestGeneratedTitles(TransactionCase):

    def test_only_the_old_template_counts_as_generated(self):
        for title, name in [('Yanmar 3TNV76-KYT', 'Yanmar 3TNV76-KYT'),
                            ('Yanmar Yanmar 3TNV70-DPE', 'Yanmar 3TNV70-DPE'),
                            ('None RG30', 'RG30'),
                            ('Yanmar, Denyo Yanmar 3TNV70-FDW', 'Yanmar 3TNV70-FDW (Denyo TLG-12ESX)'),
                            ('Yanmar Yanmar B03', 'Yanmar B03 (early model)')]:
            self.assertTrue(_generated_title(title, name, MAKES), title)
        self.assertTrue(_generated_title('Yanmar Engines 4TNE88 Engine Series', '4TNE88 Engine Series', MAKES,
                                         'Yanmar / Engines / 4TNE88 Engine Series'))
        self.assertTrue(_generated_title('Yanmar Engines 3TNC / 4TNC Engine Series', '3TNC / 4TNC Engine Series',
                                         MAKES, 'Yanmar / Engines / 3TNC / 4TNC Engine Series'))
        self.assertFalse(_generated_title('Yanmar Engines 2TNV series', '2TNV70 Engine Series', MAKES,
                                          'Yanmar / Engines / 2TNV70 Engine Series'))
        for title, name in [('Parts catalogue Yanmar B03', 'Yanmar B03'),
                            ('Spare parts catalogue for Yanmar 3TNV76', 'Yanmar 3TNV76'),
                            ('Spare parts catalogue MT 1030 S5 E3', 'Manitou MT 1030 S5 E3')]:
            self.assertFalse(_generated_title(title, name, MAKES), title)
