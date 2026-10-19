"""One-off cleanup of same-named brochures (docs/brochure_duplicates.md).

Runs before the /model/ urls go public, so the models it renames simply get a
fresh slug. Explicit rules match a brochure by the sha1 of its PDF: brochure
ids differ between databases, the files don't.
"""
import logging
from collections import defaultdict

from odoo.addons.seo_url.models.slug_mixin import slugify

_logger = logging.getLogger(__name__)

DONE_PARAM = 'brochures.duplicates_cleaned'

RENAMES = {
    # Same name, a different application or variant in the file.
    'ee8917adcdf506d29d7b432f92bcca88450db5ca': 'Kubota D1005-EKB-DENYO-2 (Denyo DLW-400ESW, DIS-90SB)',
    'bc4977187d5e6c391f81c7d586d62c4b7ad3dbaf': 'Yanmar 3TNE68-CSF / ECSF',
    '3a979255645890907f496ed80a2b36bd2e938ece': 'Yanmar 3TNE68-BE / EBE',
    'e9d030c301c08b114ebdc4c8b2b823cef72dd160': 'Yanmar V3-3 / V4-3 (US)',
    'b68c5e7f8283b53e13e6492a2b25fd5daecbf765': 'Yanmar 3TNV70-FDW (Denyo TLG-12ESX)',
    'a45ee966d12434ef2b3b8c2b2dd33a17a558b7ad': 'Yanmar 3TNV76-FDG (Denyo TLG-15ESX)',
    # Typo ("YB451-2. YB501-2"); its early-model twin takes this name too.
    '1a0c728f969b8fa96316112a5e7e7078b7e9bddb': 'Yanmar YB451-2, YB501-2',
    # Same engine, older manual next to a newer Yanmar parts catalog. Up to 104
    # parts differ and no serial range is printed, so they stay two pages.
    'fb5e8b7fc93c39fbc759428c93e7141b46fddff0': 'Yanmar 3TNE74-SA (older parts manual)',
    '3dd9f4dd8cce7068c70369780617c97a2a1eafb8': 'Yanmar 3TNE78A-MG (older parts manual)',
    '7f8eec7a5803d7b871a70441785bc19467996266': 'Yanmar 3TNE88-PG (older parts manual)',
    '65c837a02ad1842b30a5ba0745be2c7b8bf3ea23': 'Yanmar 4TNE84-SA (older parts manual)',
    '2c936109f68c4f1e4cf0172d8be9e0d13a8c7147': 'Yanmar 4TNV94L-PDBWE (older parts manual)',
}

# Proven to be the same manual (same part numbers): one page.
# {PDF of the brochure kept: PDFs of the brochures merged into it}
MERGES = {
    # 3TNE68-SA: 2014 catalog + the same catalog printed again + older manual.
    '853fe8a451e76da8d9cd0cf16592bfe70f5b16a9': ['c1d165d9b741a7249dc5e64623506f5ee4100035',
                                                 '1bb18f90e5f6dc9d3ba6c32959a110619287896a'],
    # 4TNV94L-PIK: catalog 0CD10-M80501EN, Mar 2014 edition + Apr 2013 edition.
    '783f032e95c852b55d6354745fba0cf72fbbe950': ['370a13c86b05dd9519f9e3f0af23878ee04e723d'],
}

# Same content as a file the kept brochure already has; not a second download.
DUPLICATE_FILES = {'c1d165d9b741a7249dc5e64623506f5ee4100035'}

EARLY_MODELS = 'Early Models'


def _checksums(env):
    """{brochure.attachment id: sha1 of its file}"""
    env.cr.execute("""
        SELECT res_id, checksum FROM ir_attachment
         WHERE res_model = 'brochure.attachment' AND res_field = 'attachment'
    """)
    return dict(env.cr.fetchall())


def _merge(keep, others, sums):
    """Fold `others` into `keep`: PDFs (minus duplicates), order lines,
    categories and redirects move over, then `others` go."""
    Legacy = keep.env['legacy.url'].sudo()
    kept = {sums.get(att.id) for att in keep.attachment_ids}
    for other in others - keep:
        for att in other.attachment_ids:
            checksum = sums.get(att.id)
            if checksum in kept or checksum in DUPLICATE_FILES:
                att.unlink()
            else:
                att.brochure_id = keep
                kept.add(checksum)
        other.brochure_line_ids.write({'brochure_id': keep.id})
        keep.category_ids |= other.category_ids
        # Old prod urls of the merged record now lead to the kept one. Its own
        # /model/ slug was never public, so it needs no redirect.
        Legacy.search([('res_model', '=', 'brochure'), ('res_id', '=', other.id)]).write({'res_id': keep.id})
        other.unlink()


def cleanup_duplicates(env):
    Brochure = env['brochure'].with_context(active_test=False, lang='en_US')
    sums = _checksums(env)
    by_checksum = {}
    for brochure in Brochure.search([]):
        for att in brochure.attachment_ids:
            by_checksum[sums.get(att.id)] = brochure

    def groups():
        found = defaultdict(lambda: Brochure.browse())
        for brochure in Brochure.search([]):
            found[slugify(brochure.name)] |= brochure
        return [g for g in found.values() if len(g) > 1]

    # Every same-named model gets a fresh slug at the end, so the record that
    # keeps the plain name also gets the plain url.
    affected = Brochure.browse()
    for group in groups():
        affected |= group

    for keep_sum, other_sums in MERGES.items():
        keep = by_checksum.get(keep_sum)
        others = Brochure.browse([by_checksum[s].id for s in other_sums if s in by_checksum])
        if keep and others:
            _merge(keep, others, sums)

    for checksum, name in RENAMES.items():
        brochure = by_checksum.get(checksum)
        if brochure and brochure.exists():
            brochure.name = name

    for group in groups():
        with_file = group.filtered('attachment_ids')
        # Same PDF uploaded twice in the same categories: one page.
        by_content = defaultdict(lambda: Brochure.browse())
        for brochure in with_file:
            key = (frozenset(brochure.category_ids.ids), frozenset(sums.get(a.id) for a in brochure.attachment_ids))
            by_content[key] |= brochure
        for same in by_content.values():
            if len(same) > 1:
                keep = max(same, key=lambda b: (len(b.brochure_line_ids), -b.id))
                _merge(keep, same, sums)
        # A record with no file next to one with a file is an empty shell.
        with_file = with_file.exists()
        shells = (group - with_file).exists()
        if with_file and shells:
            _merge(with_file[0], shells, sums)

    for group in groups():
        # The same model kept under "Early Models" and under its type: both
        # stay (different files), the early copy says so in its name.
        early = group.filtered(lambda b: EARLY_MODELS in b.category_ids.mapped('name'))
        current = group - early
        if early and current:
            for brochure in early:
                brochure.name = f'{current[0].name} (early model)'

    affected = affected.exists()
    affected._assign_slugs()
    env['ir.config_parameter'].sudo().set_param(DONE_PARAM, '1')
    _logger.info('[brochures] duplicate cleanup: %s same-named models now have distinct names and urls',
                 len(affected))
