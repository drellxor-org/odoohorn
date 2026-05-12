# TVH catalog → Odoo

Two-step pipeline:

1. **Convert** TVH source files into Odoo-loadable CSVs.
2. **Import** those CSVs into a running Odoo via XML-RPC.

## Step 1: convert

```bash
python3 scripts/tvh_to_odoo.py \
    --input-dir /path/to/tvh-files \
    --output-dir /path/to/output
```

Input directory is expected to contain files matching the TVH naming convention
(case-insensitive, any customer prefix):

| File pattern                       | Required | Delimiter |
| ---------------------------------- | -------- | --------- |
| `*-TLH-catalog.{csv,txt}`          | yes      | comma     |
| `*-TLH-catalog-applications.csv`   | no       | pipe `\|` |
| `*-TLH-catalog-images.csv`         | no       | semicolon |
| `*-TLH-catalog-price_list.csv`     | no       | semicolon |

Output CSVs (each row uses an external ID in the `id` column — re-runs upsert):

| File                              | Target Odoo model        |
| --------------------------------- | ------------------------ |
| `01_data_source.csv`              | `data.source`            |
| `02_product_make.csv`             | `product.make`           |
| `03_product_public_category.csv`  | `product.public.category`|
| `04_product_template.csv`         | `product.template`       |
| `05_product_application.csv`      | `product.application`    |
| `06_image_manifest.csv`           | (reference → filename)   |

## Step 2: import

The Odoo instance must have the `product_catalog` addon installed (and `brochures`
for `product.application.brochure_id`).

```bash
python3 scripts/tvh_import_rpc.py \
    --url http://localhost:8069 \
    --db silverhorn_prod \
    --user admin \
    --password admin \
    --csv-dir /path/to/output \
    --images-dir /path/to/tvh-files/images
```

The script:
- calls each model's `load()` method (same path the UI uses for CSV imports), so
  external IDs map cleanly and re-running is idempotent.
- imports in dependency order (data.source → make → category → template → application).
- after CSVs, reads each image file from `--images-dir`, base64-encodes it, and writes
  `image_1920` on the matching `product.template` (looked up by `default_code`).

Skip image import with `--skip-images`.

Credentials can be supplied via env vars instead of flags: `ODOO_URL`, `ODOO_DB`,
`ODOO_USER`, `ODOO_PASSWORD`.

## Notes

- Weights and dimensions are stored twice: the original units (`weight_gr`, `length_mm`, …)
  in new fields on `product.template`, and the Odoo-native units (`weight` in kg,
  `product_length/width/height` in cm) populated from them.
- `public_categ_ids` is set to the **deepest** Family/Subfamily/Sub-subfamily node
  present for the row (parent categories are still created so the tree is navigable).
- `product.application.brochure_id` is auto-matched after the application load: each unmatched
  application is checked against every brochure, and linked when there is exactly one brochure
  whose name tokens (alphanumeric, lowercase) are all present in the application's
  `make.name + model + serie`. Ambiguous (multi-match) and zero-match cases are left empty for
  manual mapping. Disable with `--skip-brochure-match`; tune the minimum-token threshold for
  candidate brochures with `--brochure-min-tokens N` (default 2).
- Re-importing the same source files is safe: external IDs make all operations upserts.
  Removing a row from the source files does **not** delete the corresponding Odoo record
  (`load()` does not handle deletions).
