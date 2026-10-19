# Duplicate brochure names

Generated 2026-10-14 from local `odoo-test-45` (a copy of staging data). A "group" = active brochures whose names slugify to the same value.

**38 groups, 77 brochures.** 5 have order history (keep the record with orders when merging, or move the order lines). All are published.

Columns: PDF = attachment filename; file = first 8 chars of the file checksum / size (same checksum = byte-identical PDF); desc = length of `description_sale` and its start; orders = `sale.order.brochure.line` count. Links open staging.

## A. Identical PDF, same categories (3)

Same file uploaded twice. **Merge**: keep one record, 301 the other.

### `ausa-250ah`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [16](https://dev.silverhorn.co.uk/brochure/ausa-250ah-16) | AUSA 250AH | AUSA ; AUSA / Dumpers | Parts Manual AUSA  250 AH.pdf | c080ced3/2434KB | — | 0 | 2026-07-24 |
| [17](https://dev.silverhorn.co.uk/brochure/ausa-250ah-17) | AUSA 250AH | AUSA ; AUSA / Dumpers | Parts Manual AUSA 250 AH.pdf | c080ced3/2434KB | — | 0 | 2026-07-24 |

### `toyota-2pm18-2pm20-2pm20n-serial-no-364690at-406403at`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [908](https://dev.silverhorn.co.uk/brochure/toyota-2pm18-2pm20-2pm20n-serial-no-364690at-406403at-908) | Toyota 2PM18, 2PM20, 2PM20N Serial No 364690AT - 406403AT | Toyota / Powered Pallet Trucks | Parts Manual Toyota 2PM18, 2PM20, 2PM20N Serial No 364690AT - 406403AT.pdf | 27661a2d/2314KB | — | 0 | 2026-07-24 |
| [909](https://dev.silverhorn.co.uk/brochure/toyota-2pm18-2pm20-2pm20n-serial-no-364690at-406403at-909) | Toyota 2PM18, 2PM20, 2PM20N Serial No 364690AT - 406403AT | Toyota / Powered Pallet Trucks | Toyota Parts Manual 2PM18, 2PM20, 2PM20N Serial No 364690AT - 406403AT.pdf | 27661a2d/2314KB | — | 0 | 2026-07-24 |

### `toyota-2pm18-2pm20-2pm20n-serial-no-406404at`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [910](https://dev.silverhorn.co.uk/brochure/toyota-2pm18-2pm20-2pm20n-serial-no-406404at-910) | Toyota 2PM18, 2PM20, 2PM20N Serial No 406404AT - | Toyota / Powered Pallet Trucks | Toyota Parts Manual 2PM18, 2PM20, 2PM20N Serial No 406404AT -.pdf | 3a816669/2306KB | — | 0 | 2026-07-24 |
| [911](https://dev.silverhorn.co.uk/brochure/toyota-2pm18-2pm20-2pm20n-serial-no-406404at-911) | Toyota 2PM18, 2PM20, 2PM20N Serial No 406404AT - | Toyota / Powered Pallet Trucks | Parts Manual Toyota 2PM18, 2PM20, 2PM20N Serial No 406404AT -.pdf | 3a816669/2306KB | — | 0 | 2026-07-24 |

## B. Same name, same categories, different PDFs (11)

Usually the same engine with a manual for a different application (e.g. a Denyo generator). Compare the PDFs: **merge** into one model page with several manuals, or **rename** with the application in the name.

### `kubota-d1005-ekb-denyo-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [518](https://dev.silverhorn.co.uk/brochure/kubota-d1005-ekb-denyo-2-518) | Kubota D1005-EKB-DENYO-2 | Denyo / Engines ; Kubota / Engines | Parts Manual Kubota D1005-EKB-DENYO-2.pdf | 7cc79028/4393KB | — | 0 | 2026-07-24 |
| [519](https://dev.silverhorn.co.uk/brochure/kubota-d1005-ekb-denyo-2-519) | Kubota D1005-EKB-DENYO-2 | Denyo / Engines ; Kubota / Engines | Parts Manual Kubota D1005-EKB-DENYO-2 (Denyo DLW-400ESW, DIS-90SB) Watermark.pdf | ee8917ad/4858KB | — | 0 | 2026-07-24 |

### `yanmar-3tne68-csf`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1124](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-csf-1124) | Yanmar 3TNE68-CSF | Yanmar / Engines / 3TNE68 Engine Series | Parts Manual Yanmar 3TNE68-CSF-ECSF.pdf | bc497718/1122KB | 350: We offer both genuine and aftermarket parts for 3TNE68-CSF d… | 0 | 2026-07-24 |
| [1125](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-csf-1125) | Yanmar 3TNE68-CSF | Yanmar / Engines / 3TNE68 Engine Series | 3TNE68-CSF.pdf | b57c2e6d/4254KB | 350: We offer both genuine and aftermarket parts for 3TNE68-CSF d… | 0 | 2026-07-24 |

### `yanmar-3tne68-ebe`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1128](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-ebe-1128) | Yanmar 3TNE68-EBE | Yanmar / Engines / 3TNE68 Engine Series | 3TNE68-BE_-EBE.pdf | 3a979255/3926KB | 350: We offer both genuine and aftermarket parts for 3TNE68-EBE d… | 0 | 2026-07-24 |
| [1129](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-ebe-1129) | Yanmar 3TNE68-EBE | Yanmar / Engines / 3TNE68 Engine Series | 3TNE68-EBE.pdf | 6bef4e63/3926KB | 350: We offer both genuine and aftermarket parts for 3TNE68-EBE d… | 0 | 2026-07-24 |

### `yanmar-3tne68-sa`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1153](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-sa-1153) | Yanmar 3TNE68-SA | Yanmar / Engines / 3TNE68 Engine Series | 3TNE68-G1_-SA_-G1A_-SA_-G1A_-G1A01_-G2A_-G2A01_-SA.pdf | c1d165d9/5228KB | 343: We offer both genuine and aftermarket parts for 3TNE68-SA di… | 0 | 2026-07-24 |
| [1154](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-sa-1154) | Yanmar 3TNE68-SA | Yanmar / Engines / 3TNE68 Engine Series | 3TNE68-SA.pdf | 853fe8a4/5229KB | 343: We offer both genuine and aftermarket parts for 3TNE68-SA di… | 0 | 2026-07-24 |
| [1155](https://dev.silverhorn.co.uk/brochure/yanmar-3tne68-sa-1155) | Yanmar 3TNE68-SA | Yanmar / Engines / 3TNE68 Engine Series | Parts Manual Yanmar 3TNE68-SA.pdf | 1bb18f90/1211KB | 343: We offer both genuine and aftermarket parts for 3TNE68-SA di… | 0 | 2026-07-24 |

### `yanmar-3tne74-sa`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1198](https://dev.silverhorn.co.uk/brochure/yanmar-3tne74-sa-1198) | Yanmar 3TNE74-SA | Yanmar / Engines / 3TNE74 Engine Series | Parts Manual Yanmar 3TNE74-SA.pdf | fb5e8b7f/1352KB | 314: We offer both genuine and aftermarket parts for 3TNE74-SA di… | 8 | 2026-07-24 |
| [1199](https://dev.silverhorn.co.uk/brochure/yanmar-3tne74-sa-1199) | Yanmar 3TNE74-SA | Yanmar / Engines / 3TNE74 Engine Series | 3TNE74-SA.pdf | 04ba2ec9/5100KB | 343: We offer both genuine and aftermarket parts for 3TNE74-SA di… | 0 | 2026-07-24 |

### `yanmar-3tne78a-mg`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1217](https://dev.silverhorn.co.uk/brochure/yanmar-3tne78a-mg-1217) | Yanmar 3TNE78A-MG | Yanmar / Engines / 3TNE78A Engine Series | 3TNE78A-MG.pdf | 476cb388/3308KB | 362: We offer both genuine and aftermarket parts for Yanmar 3TNE7… | 0 | 2026-07-24 |
| [1218](https://dev.silverhorn.co.uk/brochure/yanmar-3tne78a-mg-1218) | Yanmar 3TNE78A-MG | Yanmar / Engines / 3TNE78A Engine Series | Parts Manual Yanmar 3TNE78A-MG.pdf | 3dd9f4dd/1792KB | 362: We offer both genuine and aftermarket parts for Yanmar 3TNE7… | 0 | 2026-07-24 |

### `yanmar-3tne88-pg`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1328](https://dev.silverhorn.co.uk/brochure/yanmar-3tne88-pg-1328) | Yanmar 3TNE88-PG | Yanmar / Engines / 3TNE88 Engine Series | Parts Manual Yanmar 3TNE88-PG.pdf | 7f8eec7a/1170KB | 314: We offer both genuine and aftermarket parts for 3TNE88-PG di… | 0 | 2026-07-24 |
| [1329](https://dev.silverhorn.co.uk/brochure/yanmar-3tne88-pg-1329) | Yanmar 3TNE88-PG | Yanmar / Engines / 3TNE88 Engine Series | 3TNE88-PG.pdf | 8d09e84d/679KB | 314: We offer both genuine and aftermarket parts for 3TNE88-PG di… | 0 | 2026-07-24 |

### `yanmar-4tne84-sa`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1868](https://dev.silverhorn.co.uk/brochure/yanmar-4tne84-sa-1868) | Yanmar 4TNE84-SA | Yanmar / Engines / 4TNE84 Engine Series | Parts Manual Yanmar 4TNE84-SA.pdf | 65c837a0/1330KB | 314: We offer both genuine and aftermarket parts for 4TNE84-SA di… | 0 | 2026-07-24 |
| [1869](https://dev.silverhorn.co.uk/brochure/yanmar-4tne84-sa-1869) | Yanmar 4TNE84-SA | Yanmar / Engines / 4TNE84 Engine Series | Parts Manual Yanmar 4TNE84-SA.pdf | 433c321e/6700KB | 314: We offer both genuine and aftermarket parts for 4TNE84-SA di… | 0 | 2026-07-24 |

### `yanmar-4tnv94l-pdbwe`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1997](https://dev.silverhorn.co.uk/brochure/yanmar-4tnv94l-pdbwe-1997) | Yanmar 4TNV94L-PDBWE | Yanmar / Engines / 4TNV94 Engine Series | 4TNV94L-PDBWE.pdf | 41a5136d/4011KB | 344: We offer both genuine and aftermarket parts for Yanmar 4TNV9… | 0 | 2026-07-24 |
| [1998](https://dev.silverhorn.co.uk/brochure/yanmar-4tnv94l-pdbwe-1998) | Yanmar 4TNV94L-PDBWE | Yanmar / Engines / 4TNV94 Engine Series | Parts Manual Yanmar 4TNV94L-PDBWE.pdf | 2c936109/1023KB | 344: We offer both genuine and aftermarket parts for Yanmar 4TNV9… | 1 | 2026-07-24 |

### `yanmar-4tnv94l-pik`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2002](https://dev.silverhorn.co.uk/brochure/yanmar-4tnv94l-pik-2002) | Yanmar 4TNV94L-PIK | Yanmar / Engines / 4TNV94 Engine Series | 4TNV94L-PIK.pdf | 370a13c8/4830KB | 332: We offer both genuine and aftermarket parts for Yanmar 4TNV9… | 0 | 2026-07-24 |
| [2003](https://dev.silverhorn.co.uk/brochure/yanmar-4tnv94l-pik-2003) | Yanmar 4TNV94L-PIK | Yanmar / Engines / 4TNV94 Engine Series | Parts Manual Yanmar 4TNV94L-PIK.pdf | 783f032e/2110KB | 332: We offer both genuine and aftermarket parts for Yanmar 4TNV9… | 0 | 2026-07-24 |

### `yanmar-v3-3-v4-3`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2284](https://dev.silverhorn.co.uk/brochure/yanmar-v3-3-v4-3-2284) | Yanmar V3-3 / V4-3 | Yanmar / Wheel Loaders | Parts Manual V3-3 (US) and V4-3 (US).pdf | e9d030c3/3200KB | — | 0 | 2026-07-24 |
| [2285](https://dev.silverhorn.co.uk/brochure/yanmar-v3-3-v4-3-2285) | Yanmar V3-3 / V4-3 | Yanmar / Wheel Loaders | Parts Manual Yanmar V3-3 and V4-3.pdf | c1f85498/3709KB | — | 0 | 2026-07-24 |

## C. Same name, different categories (24)

Usually an engine listed both under its maker and under the machine maker. Often a true duplicate; decide the primary category, then merge or rename.

### `toyota-8fg30b-g858`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [939](https://dev.silverhorn.co.uk/brochure/toyota-8fg30b-g858-939) | Toyota 8FG30B (G858) | Toyota / Forklifts | Parts Manual Toyota 8FG30B (G858).pdf | 60059d07/6594KB | — | 0 | 2026-07-24 |
| [940](https://dev.silverhorn.co.uk/brochure/toyota-8fg30b-g858-940) | Toyota 8FG30B (G858) | — | — | — | — | 0 | 2026-07-24 |

### `yanmar-3tne88-ebvc`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1308](https://dev.silverhorn.co.uk/brochure/yanmar-3tne88-ebvc-1308) | Yanmar 3TNE88-EBVC | — | — | — | — | 0 | 2026-07-24 |
| [1309](https://dev.silverhorn.co.uk/brochure/yanmar-3tne88-ebvc-1309) | Yanmar 3TNE88-EBVC | Yanmar / Engines / 3TNE88 Engine Series | Parts Manual Yanmar 3TNE88-EBVC (S4130,50).pdf | 9812be48/1427KB | 326: We offer both genuine and aftermarket parts for 3TNE88-EBVC … | 0 | 2026-07-24 |

### `yanmar-3tnv70-fdw`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1399](https://dev.silverhorn.co.uk/brochure/yanmar-3tnv70-fdw-1399) | Yanmar 3TNV70-FDW | Yanmar / Engines / 3TNV70 Engine Series | 3TNV70-FDW.pdf | 9f06180d/3965KB | 332: We offer both genuine and aftermarket parts for Yanmar 3TNV7… | 0 | 2026-07-24 |
| [1400](https://dev.silverhorn.co.uk/brochure/yanmar-3tnv70-fdw-1400) | Yanmar 3TNV70-FDW | Denyo / Engines ; Yanmar / Engines / 3TNV70 Engine Series | Parts Manual Yanmar 3TNV70-FDW (DENYO TLG-12ESX).pdf | b68c5e7f/1693KB | 332: We offer both genuine and aftermarket parts for Yanmar 3TNV7… | 0 | 2026-07-24 |

### `yanmar-3tnv76-fdg`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [1465](https://dev.silverhorn.co.uk/brochure/yanmar-3tnv76-fdg-1465) | Yanmar 3TNV76-FDG | Denyo / Engines ; Yanmar / Engines / 3TNV76 Engine Series | Parts Manual Yanmar 3TNV76-FDG (DENYO TLG-15ESX).pdf | a45ee966/1675KB | 356: We offer both genuine and aftermarket parts for Yanmar 3TNV7… | 0 | 2026-07-24 |
| [1466](https://dev.silverhorn.co.uk/brochure/yanmar-3tnv76-fdg-1466) | Yanmar 3TNV76-FDG | Yanmar / Engines / 3TNV76 Engine Series | 3TNV76-FDG.pdf | 4abc36f3/4205KB | 357: We offer both genuine and aftermarket parts for Yanmar 3TNV7… | 0 | 2026-07-24 |

### `yanmar-b03`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2148](https://dev.silverhorn.co.uk/brochure/yanmar-b03-2148) | Yanmar B03 | Yanmar / Early Models | Parts Manual Yanmar B03.pdf | f9e8db0c/1644KB | — | 0 | 2026-07-24 |
| [2149](https://dev.silverhorn.co.uk/brochure/yanmar-b03-2149) | Yanmar B03 | Yanmar / Excavators | Parts Manual Yanmar B03.pdf | aaffb51f/1342KB | — | 0 | 2026-07-24 |

### `yanmar-b12-2b-b17-2b`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2155](https://dev.silverhorn.co.uk/brochure/yanmar-b12-2b-b17-2b-2155) | Yanmar B12-2B B17-2B | Yanmar / Early Models | Parts Manual Yanmar B12-2B B17-2B.pdf | 25300933/3187KB | — | 0 | 2026-07-24 |
| [2156](https://dev.silverhorn.co.uk/brochure/yanmar-b12-2b-b17-2b-2156) | Yanmar B12-2B, B17-2B | Yanmar / Excavators | Parts Manual Yanmar B12-2B B17-2B.pdf | 22c67f98/2952KB | — | 0 | 2026-07-24 |

### `yanmar-b15`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2159](https://dev.silverhorn.co.uk/brochure/yanmar-b15-2159) | Yanmar B15 | Yanmar / Early Models | Parts Manual Yanmar B15.pdf | 8463b3b9/2045KB | — | 0 | 2026-07-24 |
| [2160](https://dev.silverhorn.co.uk/brochure/yanmar-b15-2160) | Yanmar B15 | Yanmar / Excavators | Parts Manual Yanmar B15.pdf | bfcf9578/1836KB | — | 7 | 2026-07-24 |

### `yanmar-b2-5`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2164](https://dev.silverhorn.co.uk/brochure/yanmar-b2-5-2164) | Yanmar B2-5 | Yanmar / Early Models | Parts Manual Yanmar B2-5.pdf | 58d27732/3599KB | — | 0 | 2026-07-24 |
| [2165](https://dev.silverhorn.co.uk/brochure/yanmar-b2-5-2165) | Yanmar B2-5 | Yanmar / Excavators | Parts Manual Yanmar B2-5.pdf | fe0436e4/2981KB | — | 0 | 2026-07-24 |

### `yanmar-b25v-1`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2171](https://dev.silverhorn.co.uk/brochure/yanmar-b25v-1-2171) | Yanmar B25V-1 | Yanmar / Excavators | Parts Manual Yanmar B25V-1.pdf | 0c08fd7d/364KB | — | 0 | 2026-07-24 |
| [2172](https://dev.silverhorn.co.uk/brochure/yanmar-b25v-1-2172) | Yanmar B25V-1 | Yanmar / Early Models | Parts Manual Yanmar B25V-1.pdf | 7199b898/769KB | — | 0 | 2026-07-24 |

### `yanmar-b2u-1`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2177](https://dev.silverhorn.co.uk/brochure/yanmar-b2u-1-2177) | Yanmar B2U-1 | Yanmar / Early Models | Parts Manual Yanmar B2U-1.pdf | ef61def5/3242KB | — | 0 | 2026-07-24 |
| [2178](https://dev.silverhorn.co.uk/brochure/yanmar-b2u-1-2178) | Yanmar B2U-1 | Yanmar / Excavators | Parts Manual Yanmar B2U-1.pdf | 641512df/3058KB | — | 0 | 2026-07-24 |

### `yanmar-b50-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2191](https://dev.silverhorn.co.uk/brochure/yanmar-b50-2-2191) | Yanmar B50-2 | Yanmar / Excavators | Parts Manual Yanmar B50-2.pdf | 60996d73/5189KB | — | 0 | 2026-07-24 |
| [2192](https://dev.silverhorn.co.uk/brochure/yanmar-b50-2-2192) | Yanmar B50-2 | Yanmar / Early Models | Parts Manual Yanmar B50-2.pdf | c8f2f6e5/2661KB | — | 0 | 2026-07-24 |

### `yanmar-b6-3`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2200](https://dev.silverhorn.co.uk/brochure/yanmar-b6-3-2200) | Yanmar B6-3 | Yanmar / Excavators | Parts Manual Yanmar B6-3.pdf | 6f9451c1/7608KB | — | 0 | 2026-07-24 |
| [2201](https://dev.silverhorn.co.uk/brochure/yanmar-b6-3-2201) | Yanmar B6-3 | Yanmar / Early Models | Parts Manual Yanmar B6-3.pdf | a181ae1d/7328KB | — | 0 | 2026-07-24 |

### `yanmar-b7`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2203](https://dev.silverhorn.co.uk/brochure/yanmar-b7-2203) | Yanmar B7 | Yanmar / Early Models | Parts Manual Yanmar B7.pdf | 77d36a99/3853KB | — | 0 | 2026-07-24 |
| [2204](https://dev.silverhorn.co.uk/brochure/yanmar-b7-2204) | Yanmar B7 | Yanmar / Excavators | Parts Manual Yanmar B7.pdf | 725a7a28/3782KB | — | 0 | 2026-07-24 |

### `yanmar-sv08`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2269](https://dev.silverhorn.co.uk/brochure/yanmar-sv08-2269) | Yanmar SV08 | Yanmar / Early Models | Parts Manual Yanmar SV08.pdf | 8363594b/2787KB | — | 0 | 2026-07-24 |
| [2270](https://dev.silverhorn.co.uk/brochure/yanmar-sv08-2270) | Yanmar SV08 | Yanmar / Excavators | Parts Manual Yanmar SV08.pdf | d94af695/3618KB | — | 0 | 2026-07-24 |

### `yanmar-vio15-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2298](https://dev.silverhorn.co.uk/brochure/yanmar-vio15-2-2298) | Yanmar VIO15-2 | Yanmar / Excavators | Parts Manual Yanmar VIO15-2.pdf | 53aa41c4/5023KB | — | 0 | 2026-07-24 |
| [2299](https://dev.silverhorn.co.uk/brochure/yanmar-vio15-2-2299) | Yanmar VIO15-2 | Yanmar / Early Models | Parts Manual Yanmar VIO15-2.pdf | e41ef42b/4762KB | — | 0 | 2026-07-24 |

### `yanmar-vio20-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2306](https://dev.silverhorn.co.uk/brochure/yanmar-vio20-2-2306) | Yanmar VIO20-2 | Yanmar / Excavators | Parts Manual Yanmar VIO20-2.pdf | f5111155/5580KB | — | 0 | 2026-07-24 |
| [2307](https://dev.silverhorn.co.uk/brochure/yanmar-vio20-2-2307) | Yanmar VIO20-2 | Yanmar / Early Models | Parts Manual Yanmar VIO20-2.pdf | 82f45d6d/4130KB | — | 0 | 2026-07-24 |

### `yanmar-vio20-3`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2308](https://dev.silverhorn.co.uk/brochure/yanmar-vio20-3-2308) | Yanmar VIO20-3 | Yanmar / Early Models | Parts Manual Yanmar VIO20-3.pdf | 233fb9f8/3776KB | — | 0 | 2026-07-24 |
| [2309](https://dev.silverhorn.co.uk/brochure/yanmar-vio20-3-2309) | Yanmar VIO20-3 | Yanmar / Excavators | Parts Manual Yanmar VIO20-3.pdf | 6b80e47c/10362KB | — | 1 | 2026-07-24 |

### `yanmar-vio27-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2312](https://dev.silverhorn.co.uk/brochure/yanmar-vio27-2-2312) | Yanmar VIO27-2 | Yanmar / Excavators | Parts Manual Yanmar VIO27-2.pdf | bb853a41/6390KB | — | 0 | 2026-07-24 |
| [2313](https://dev.silverhorn.co.uk/brochure/yanmar-vio27-2-2313) | Yanmar VIO27-2 | Yanmar / Early Models | Parts Manual Yanmar VIO27-2.pdf | 98e214d0/4414KB | — | 0 | 2026-07-24 |

### `yanmar-vio40-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2325](https://dev.silverhorn.co.uk/brochure/yanmar-vio40-2-2325) | Yanmar VIO40-2 | Yanmar / Excavators | Parts Manual Yanmar VIO40-2.pdf | 72e2253b/5554KB | — | 0 | 2026-07-24 |
| [2326](https://dev.silverhorn.co.uk/brochure/yanmar-vio40-2-2326) | Yanmar VIO40-2 | Yanmar / Early Models | Parts Manual Yanmar VIO40-2.pdf | c3c3e1a4/2729KB | — | 0 | 2026-07-24 |

### `yanmar-vio50`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2333](https://dev.silverhorn.co.uk/brochure/yanmar-vio50-2333) | Yanmar VIO50 | Yanmar / Early Models | Parts Manual Yanmar VIO50.pdf | 29fac818/4833KB | — | 0 | 2026-07-24 |
| [2334](https://dev.silverhorn.co.uk/brochure/yanmar-vio50-2334) | Yanmar VIO50 | Yanmar / Excavators | Parts Manual Yanmar VIO50.pdf | ea41cbb5/5461KB | — | 1 | 2026-07-24 |

### `yanmar-vio70`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2343](https://dev.silverhorn.co.uk/brochure/yanmar-vio70-2343) | Yanmar VIO70 | Yanmar / Early Models | Parts Manual Yanmar VIO70.pdf | b3af00c1/2964KB | — | 0 | 2026-07-24 |
| [2344](https://dev.silverhorn.co.uk/brochure/yanmar-vio70-2344) | Yanmar VIO70 | Yanmar / Excavators | Parts Manual Yanmar VIO70.pdf | 2cdeb3f8/7145KB | — | 0 | 2026-07-24 |

### `yanmar-vio75`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2346](https://dev.silverhorn.co.uk/brochure/yanmar-vio75-2346) | Yanmar VIO75 | Yanmar / Early Models | Parts Manual Yanmar VIO75.pdf | efce5081/2849KB | — | 0 | 2026-07-24 |
| [2347](https://dev.silverhorn.co.uk/brochure/yanmar-vio75-2347) | Yanmar VIO75 | Yanmar / Excavators | Parts Manual Yanmar VIO75.pdf | a581768c/5366KB | — | 0 | 2026-07-24 |

### `yanmar-yb271-b27-b27-1`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2361](https://dev.silverhorn.co.uk/brochure/yanmar-yb271-b27-b27-1-2361) | Yanmar YB271 B27 B27-1 | Yanmar / Early Models | Parts Manual Yanmar YB271 B27 B27-1.pdf | f5b8dd35/4181KB | — | 0 | 2026-07-24 |
| [2362](https://dev.silverhorn.co.uk/brochure/yanmar-yb271-b27-b27-1-2362) | Yanmar YB271, B27, B27-1 | Yanmar / Excavators | Parts Manual Yanmar YB271 B27 B27-1.pdf | 01af575b/3558KB | — | 0 | 2026-07-24 |

### `yanmar-yb451-2-yb501-2`

| id | name | categories | PDF | file | desc | orders | created |
|---|---|---|---|---|---|---|---|
| [2370](https://dev.silverhorn.co.uk/brochure/yanmar-yb451-2-yb501-2-2370) | Yanmar YB451-2 YB501-2 | Yanmar / Early Models | Parts Manual Yanmar YB451-2 YB501-2.pdf | 987dc5da/3748KB | — | 0 | 2026-07-24 |
| [2371](https://dev.silverhorn.co.uk/brochure/yanmar-yb451-2-yb501-2-2371) | Yanmar YB451-2. YB501-2 | Yanmar / Excavators | Parts Manual Yanmar YB451-2 YB501-2.pdf | 1a0c728f/3112KB | — | 0 | 2026-07-24 |

---

## Actions (implemented: `addons/brochures/duplicates.py`)

Runs once per database before the `/model/` urls go public: inside the brochures install hook on prod, as an update-time function on databases migrated earlier. Explicit rules match a model by the sha1 of its PDF (ids differ between databases). Tested on the July prod snapshot: 2,371 → 2,363 models, no same-named models left; prod sitemap redirects unchanged (88/88, 1233/1235, 42/42).

- **A. Same PDF, same categories → merged** (AUSA 250AH, both Toyota 2PM18 pairs). The record with order history (else the oldest) stays; old urls of the other 301 to it.
- **PDF check (7 groups):** same engine, newer Yanmar *PARTS CATALOG* (2013–2014) next to an older parts manual. No serial range is printed in either, so:
  - **Merged** where the part numbers prove it is the same manual: 3TNE68-SA (3 records, identical parts; one catalog was printed twice and is dropped) and 4TNV94L-PIK (Mar 2014 edition = Apr 2013 + 5 parts). One page, both PDFs.
  - **Kept as two pages** where 23–104 parts differ (3TNE74-SA, 3TNE78A-MG, 3TNE88-PG, 4TNE84-SA, 4TNV94L-PDBWE): the newer catalog keeps the plain name and url, the older one becomes `… (older parts manual)`.
- **B renames:** 519 → `Kubota D1005-EKB-DENYO-2 (Denyo DLW-400ESW, DIS-90SB)`, `Yanmar 3TNE68-CSF / ECSF`, `Yanmar 3TNE68-BE / EBE`, `Yanmar V3-3 / V4-3 (US)`, Denyo manuals `Yanmar 3TNV70-FDW (Denyo TLG-12ESX)` / `Yanmar 3TNV76-FDG (Denyo TLG-15ESX)`.
- **C. Copies without a file → removed** (Toyota 8FG30B (G858), Yanmar 3TNE88-EBVC); their old urls 301 to the copy with the file.
- **C. "Early Models" vs "Excavators" → both kept**; the early copy is named `{name} (early model)` (`/model/yanmar-b03-early-model`), the other keeps the plain url. `YB451-2. YB501-2` typo fixed to `YB451-2, YB501-2`.
