# STEC evidence files

Read by `ml-engine/carbon/stec_evidence.py`. Add rows only with a verifiable source;
an empty file means "no sourced evidence", and results then carry an explicit proxy label.

| File | Columns | Status |
|---|---|---|
| `fab-provenance.csv` | vendor, type, product, process_node_nm, manufacturing_region, foundry, confidence, source | 11 products from NVIDIA architecture whitepapers (A100, GA102, GV100) |
| `chiplets.csv` | product, die_role, die_count, die_area_mm2, node_nm, manufacturing_region, foundry, confidence, source | 4 AMD products (ISSCC 2020; Zen 3 CCD area to verify) |
| `fab-rules.csv` | vendor, type, node_nm (`*` = any), candidate_regions (`;`), foundry (`;`), confidence, basis | **Assumptions** per vendor/type/node; several candidates produce a range |
| `manufacturing-years.csv` | product, release_year, manufacturing_year, source | empty: release year is used as a labeled proxy |
| `yields.csv` | process_node_nm, foundry, year, yield_factor (0-1], source | empty: no yield correction |
| `market-factors.csv` | foundry, year, market_based_factor_g_co2e_per_kwh, contract_type, source | empty: market-based STEC is `not_available` |

Region names must match the entity names in `data/raw/grid/owid-carbon-intensity-electricity.csv`
(for example `Taiwan`, `South Korea`, `United States`, `Ireland`, `Israel`).

Known CarbonSet data issues found while building these files:

- AMD chiplet products list only CCD area (EPYC 7742 is recorded as one 74 mm2 die; Ryzen 9 5950X as 2x74 mm2 without the IO die).
- `RTX 3090Ti` has release date 2020-01-01 in CarbonSet.
