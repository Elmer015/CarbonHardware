# Phase 2: Dataset Inspection and Research Mapping

**Inspection date:** 2026-10-13  
**Repository:** CarbonHardware  
**Scope:** inspection and research mapping only. No preprocessing, dataset merging, feature engineering, or model training was performed.

## Executive Findings

- `data/raw/scarif/`, `data/raw/carbonset/`, and `data/raw/environmental/` exist but contain no local files at the time of inspection.
- The project README files and the existing processing, carbon, and uncertainty modules are empty. Therefore there is no project-local schema, target definition, unit convention, or TPU/A100 record to validate.
- The local dataset cannot currently provide any actual embodied-carbon labels. No labels were fabricated.
- `ml-engine/data_processing/inspect_dataset.py` now inspects local `.csv`, `.xls`, `.xlsx`, and `.xlsm` files, including all Excel sheets. It reports rows, columns, dtypes, missingness, duplicates, numeric descriptive statistics, visible unit tokens in column names, and candidate target names. A candidate is not treated as a verified target.
- Public documentation identifies SCARIF as a server-level embodied-carbon estimator and CarbonSet as a processor CFP dataset/modeling repository. These are related but do not have interchangeable target definitions.

## Local Inventory

| Path | Result | Limitation |
|---|---|---|
| `data/raw/scarif/` | Empty | No local SCARIF files to inspect |
| `data/raw/carbonset/` | Empty | No local CarbonSet files to inspect |
| `data/raw/environmental/` | Empty | No environmental, lifecycle, or e-waste files to inspect |
| `docs/` | Existing files are empty | No project research document or uncertainty framework was available locally |
| `ml-engine/` | Relevant modules are empty | No existing target or unit contract was available |

Run the inspector from the repository root with:

```text
python ml-engine/data_processing/inspect_dataset.py --json-output data/interim/dataset-inspection.json --markdown-output data/interim/dataset-inspection.md
```

The script does not download data and does not alter input files. CSV parsing uses pandas; Excel parsing uses pandas with the already-declared `openpyxl` dependency for common modern workbooks. Legacy `.xls` files may additionally require an installed Excel engine.

## Source Mapping

### SCARIF

- URL: https://github.com/arc-research-lab/SCARIF
- Access date: 2026-10-13
- Repository documentation describes SCARIF v0.2 as a tool for estimating embodied carbon of data-center servers with accelerator hardware, including peripheral server parts.
- The README identifies `original_data/` as vendor carbon-footprint-report data for HP, Dell, and Lenovo, and describes a feature-extraction notebook and statistical model.
- The documented inputs include CPU core count, DRAM size, SSD size, HDD size, release year, and optional accelerator technology node and chip area.
- The README documents examples involving a Dell R740 + V100 and a Dell R750 + A100. This is evidence of example/model coverage, not a complete A100 lifecycle inventory.
- License shown by the repository page: MIT. The ACT submodule and any vendor reports may have their own terms and should be checked separately before redistribution.
- **Embodied-carbon labels:** the repository documentation indicates vendor carbon-footprint reports and a server-level estimator, but no SCARIF files are present locally and no column-level labels were verified in this project.
- Limitation: SCARIF's output is server-level estimation. It must not be merged directly with chip-level CarbonSet ECFP or paper-level lifecycle totals without aligning system boundary, functional unit, allocation, and units.

### CarbonSet

- URL: https://github.com/advent-lab/CarbonSet
- Access date: 2026-10-13
- Repository documentation describes `dataset/CarbonSet.csv` as the main dataset and says it covers more than 1,600 desktop and datacenter processors.
- The documented metric families include design metrics, performance metrics, ECFP (embodied carbon footprint), OCFP (operational carbon footprint), total CFP, and composite performance/CFP metrics.
- The repository says CFP values are modeled using an enhanced ECO-CHIP and that probabilistic inputs can produce a distribution of CFP outputs. This is relevant to uncertainty, but it is not automatically the same uncertainty model required by this project.
- The README references the base chip dataset, Geekbench-OpenCL, PassMark, and ECO-CHIP. These are provenance dependencies, not proof that every source file is included in this workspace.
- License: no license was identified in the repository-page material inspected on 2026-10-13. Confirm the repository and each dependency's terms before copying data.
- **Embodied-carbon labels:** the public README explicitly describes ECFP, but the actual CSV is not present locally. The label definition, unit, boundary, and row-level availability must be verified after an approved download.
- Limitation: CarbonSet is processor-focused and modeled. It should not be treated as an empirical product environmental declaration or automatically combined with SCARIF server estimates.
- **Unit evidence added 2026-10-13:** the supplied CarbonSet paper PDF (arXiv:2506.10373v1) labels CFP distributions as `kg CO2 eq.` and states that ECFP/CFP values are modeled across the processor lifecycle. It also states that the mean CFP from 10,000 simulations is used as the final representative value. Therefore `Emb_Carbon_Mean` may be prepared as `kg_co2e`, with the important limitation that it is a probabilistic ECO-CHIP model output, not a direct measurement.

### Research papers and frameworks listed in the brief

The exact URLs, PDFs, supplementary files, and licenses for the following items were not present in the workspace and were not downloaded:

| Reference | Evidence available now | Dataset implication |
|---|---|---|
| *Life-Cycle Emissions of AI Hardware: A Cradle-To-Grave Approach and Generational Trends* | Title only in the brief | Obtain the paper/supplement and record functional unit, life-cycle stages, hardware generations, and uncertainty inputs before use |
| *More than Carbon: Cradle-to-Grave environmental impacts of GenAI training on the Nvidia A100 GPU* | Title only in the brief | Treat as an A100 lifecycle source only after verifying whether values are measured, modeled, or scenario-specific and whether downloadable tables exist |
| *Spatial-Temporal Embodied Carbon Models With Dual Carbon Attribution for Embodied Carbon Accounting of Computer Systems* | Title only in the brief | Likely methodological support for spatial/temporal attribution; no local labels or machine-readable data were verified |
| Project uncertainty framework | No local research document was available | Do not implement a specific distribution or confidence interval until the cited framework is supplied |
| PCF-RWKV-related research | No local citation or data file was available | Use only for methodology/provenance after locating the exact paper, code, and license; do not infer hardware labels from it |

## TPU and A100 Mapping

No TPU generation records are present in the local raw directories. The five-generation TPU cohort requested by the brief is therefore a **research requirement**, not an available local dataset. No source was verified here for the exact v4i-through-v6e generation rows, manufacturing inventories, lifetimes, or end-of-life values.

| Requested hardware scope | Verified available source | Current status |
|---|---|---|
| TPU v4i through v6e, five generations per brief | None in local files; SCARIF README concerns generic accelerator/server estimation and documents V100/A100 examples, not these TPU rows | Obtain authoritative generation specifications and lifecycle/embodied labels; keep each generation as a source-anchored row |
| NVIDIA A100 lifecycle | A100 appears in SCARIF's documented R750 example; the A100 cradle-to-grave paper is only named in the brief | SCARIF example is not a lifecycle dataset; obtain and verify the paper's tables/supplement before using A100 lifecycle values |
| Processor-level A100-like CFP | CarbonSet documentation says it covers datacenter GPUs and ECFP, but the local CSV is absent | Candidate source only; verify whether A100 is a row and what ECFP boundary/unit it uses |

The recommended cross-source key is `hardware_model`, `generation`, `source_id`, `functional_unit`, `system_boundary`, `geography`, `time_period`, and `unit`. Do not join rows on model name alone.

## Requirements by Research Output

### STEC

STEC requirements cannot be finalized without the cited definition. At minimum, the eventual source contract must identify the activity being measured, energy/time basis, hardware scope, utilization assumptions, location/grid factor, and unit. The inspector should preserve these as separate fields rather than collapsing them into a generic carbon column.

### CCI

CCI requirements cannot be finalized because the project-local definition is absent. Record the exact formula, numerator/denominator, time basis, and whether the index uses operational, embodied, or total carbon. A CCI value without that metadata is not comparable across sources.

### Uncertainty

CarbonSet documentation supports probabilistic modeling, but the project's cited uncertainty framework is unavailable locally. Required metadata includes input distribution, parameter source, number of samples or analytical method, central estimate, interval/quantiles, and whether uncertainty is epistemic or aleatory. Do not substitute CarbonSet's distribution for the project framework without a documented justification.

### E-waste

No local e-waste labels, mass flows, lifetime assumptions, recycling rates, or end-of-life allocation factors were found. Required fields should distinguish hardware mass, replacement/discard event, lifetime, reuse/refurbishment, recycling/disposal route, and the source unit/boundary. Embodied carbon labels alone cannot be used as e-waste labels.

## Recommended Dataset Strategy

1. Obtain only the small, relevant source artifacts after approval: SCARIF `original_data`/required model files, CarbonSet's `CarbonSet.csv` or documented generation path, and paper supplements or tables for the TPU and A100 studies. Record commit or release identifiers and checksums.
2. Run the new inspector on each source independently. Preserve per-file and per-sheet reports, including dtypes, missingness, duplicates, descriptive statistics, and candidate targets.
3. Create source-specific staging tables rather than concatenating files. Add provenance and target-definition metadata before any comparison.
4. Define a canonical observation contract with explicit `value`, `unit`, `functional_unit`, `boundary`, `geography`, `time_period`, `uncertainty`, and `source_id` fields. Keep chip-level, server-level, operational, embodied, and total values separate.
5. Use CarbonSet as a potential processor-level modeled source, SCARIF as a potential server-level estimator/reference, and the lifecycle papers as separate cradle-to-grave evidence. Reconcile them only in a documented scenario layer.
6. Build the TPU v4i-through-v6e and A100 mapping only from rows or tables with traceable source evidence. Missing generations remain missing; they should not be imputed during this phase.
7. After the research document and exact uncertainty citation are added, specify STEC, CCI, and e-waste schemas. Preprocessing and training are intentionally deferred to the next phase.

## Phase 2 Stop Condition

Phase 2 inspection and mapping is complete for the currently available evidence. There are no local datasets to profile beyond empty directories, no verified local embodied-carbon labels, and no basis to preprocess or train a model. The next input needed is approved source acquisition plus the missing paper URLs/supplements and project definitions for STEC, CCI, uncertainty, and e-waste.

## Phase 3: Preprocessing and Validation

Phase 3 is implemented but remains blocked for supervised preparation until an approved source file and verified labels are supplied.

### Data contract

- `prepare_dataset.py` accepts one source at a time: `scarif`, `carbonset`, or `environmental`. It never concatenates these sources automatically because their documented boundaries and target definitions differ.
- The caller must provide `--target-column`, `--target-definition`, `--target-source-unit`, `--target-unit`, and `--group-column`. The pipeline does not infer a target or unit from a column name.
- The target is explicitly intended to be a verified embodied-carbon label. Its unit is recorded in the preprocessing report. The current repository has no such label.
- A hardware group is required for leakage-safe splitting. It represents the identity whose related observations must stay in one partition; the pipeline does not guess this identity.
- All tables within the selected source must have the same schema. Incompatible tables are reported and left separate rather than merged by guessed names or column position.

### Cleaning rules

`clean_data.py` operates on copies and leaves raw files unchanged. It removes all-empty rows, exact duplicate rows, missing/non-numeric/negative target rows, and rows missing required numeric features. It performs no imputation. Missing hardware groups are excluded because they cannot be assigned safely to a leakage-controlled split. The cleaning report records every removal count.

Only these explicit CO2e conversions are supported: `g_co2e <-> kg_co2e` and `t_co2e <-> kg_co2e`. Any other conversion is rejected until its definition is justified. Values are never converted merely because a column name contains a unit-like token.

### Feature rules

`feature_engineering.py` retains explicitly requested numeric hardware features, or safe numeric candidates when none are specified. It excludes the target, group identifier, and names containing target-like fragments such as `carbon`, `ecfp`, `ocfp`, `label`, or `target`. It performs no scaling, encoding, or imputation because the available schema is not yet known.

### Split and leakage rules

`prepare_dataset.py` uses `GroupShuffleSplit` twice with default seed `42`: first to hold out test groups, then to split the remaining groups into training and validation. The resulting hardware-group sets are checked for pairwise disjointness. At least three distinct groups are required. Exact duplicates are removed before splitting.

### Outputs

- Intermediate cleaned data: `data/interim/<source>-cleaned.csv`
- Validation and transformation report: `data/interim/preprocessing-report.json`
- Prepared partitions: `data/processed/<source>-train.csv`, `<source>-validation.csv`, and `<source>-test.csv`
- Raw files are never overwritten.

With the current empty raw directories, the command below intentionally returns status `blocked` and exit code 2:

```text
python ml-engine/data_processing/prepare_dataset.py --source carbonset
```

The required next input is an approved source artifact containing non-fabricated embodied-carbon labels, an authoritative source unit and target definition, and a hardware identity/group field. No prepared dataset is produced until those requirements are met.

### Tests

Focused preprocessing tests are in `ml-engine/tests/test_preprocessing.py`. They cover unit conversion restrictions, missing-target blocking, invalid/missing/duplicate handling, target-like feature exclusion, and group-disjoint splitting.

## Phase 4: Embodied-Carbon Estimation Model

Phase 4 model code is implemented but training is currently blocked because the Phase 3 report is not `prepared` and no validated train/validation/test files exist.

### Methodology boundary

The local SCARIF research mapping supports only a limited analogy: SCARIF estimates server-level embodied carbon from hardware/configuration inputs and vendor carbon-footprint data using a statistical model. The available documentation does not establish Random Forest as SCARIF's original algorithm, so this project labels its Random Forest as an **experimental candidate**, not a SCARIF reproduction or validated estimator.

### Model workflow

- [train.py](../ml-engine/models/train.py) reads only the Phase 3 contract and prepared splits for one source. It refuses missing, blocked, incompatible, nonnumeric, or overlapping-group data.
- A mean `DummyRegressor` is the simple baseline. A `RandomForestRegressor` is evaluated only when all validated features are numeric.
- Both candidates are fit on training data only. The validation split selects the candidate by MAE, with RMSE as the tie-breaker. The selected model is evaluated once on the held-out test split.
- [evaluate.py](../ml-engine/models/evaluate.py) records MAE, RMSE, R-squared when mathematically defined, residual bias, residual spread, quantiles, and optional per-hardware-group error patterns.
- [predict.py](../ml-engine/models/predict.py) loads the `joblib` artifact and rejects missing, nonnumeric, or missing-valued prediction features.

### Reproducibility and artifact metadata

The saved artifact metadata records the model type, experimental status, methodology limitation, source, dataset version, random seed, feature definitions, target column, target unit, target definition, group column, validation comparison, held-out test metrics, split row counts, and residual summaries. Default seed is `42`.

Expected outputs after valid Phase 3 data exists:

- `ml-engine/artifacts/embodied_carbon_model.joblib`
- `ml-engine/artifacts/embodied_carbon_model.json`

Training is intentionally not run in the current repository. The command will fail with a clear `NoValidatedDatasetError` until Phase 3 produces a prepared contract:

```text
python ml-engine/models/train.py --source carbonset --dataset-version <approved-version>
```

Model artifact tests are in [test_models.py](../ml-engine/tests/test_models.py). They require explicit `CARBONHARDWARE_MODEL_PATH` and `CARBONHARDWARE_PREDICTION_INPUT` environment variables so tests cannot silently use an unapproved or fabricated model. Before the supplied CarbonSet paper and dataset were added, the pipeline correctly reported `blocked`; the actual run and metrics are recorded below.

### Actual Phase 4 run: 2026-10-13

The supplied CarbonSet paper established the target unit as `kg CO2e`, so Phase 3 was run with `Emb_Carbon_Mean`, `Product` grouping, and the five numeric hardware features listed above. The 1,320 input rows produced 1,303 rows after removing 17 exact duplicates. The grouped split contained 776 training rows, 261 validation rows, and 266 test rows.

Validation selected `RandomForestRegressor(max_depth=10, min_samples_leaf=1, n_estimators=100, random_state=42)` over the mean baseline. Validation metrics for the selected model were MAE `0.1796288414 kg CO2e`, RMSE `1.9538346419 kg CO2e`, and R-squared `0.9795830377`. On the held-out test split, the actual metrics were:

| Metric | Held-out test result |
|---|---:|
| MAE | 0.2779047651 kg CO2e |
| RMSE | 2.4290304496 kg CO2e |
| R-squared | 0.9466518756 |

The test residual mean was `-0.2247185414 kg CO2e`, residual standard deviation was `2.4186133429 kg CO2e`, and maximum absolute error was `27.5321171644 kg CO2e`. The large gap between MAE and RMSE indicates at least one influential outlier; the model should therefore be treated as an experimental CarbonSet estimator, not a validated general-purpose estimator or a SCARIF reproduction. The artifact and full residual-by-product metadata are saved under `ml-engine/artifacts/`.
