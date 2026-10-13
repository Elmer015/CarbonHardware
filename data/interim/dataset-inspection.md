# Dataset Inspection Report

Data root: `D:\COLLEGE\SEM 5\Research Method\CarbonHardware\data\raw`

## scarif

Available local data: **False**
Limitation: No supported local CSV or Excel files were found.
## carbonset

Available local data: **True**
Files: `D:\COLLEGE\SEM 5\Research Method\CarbonHardware\data\raw\carbonset\CarbonSet.csv`

### `D:\COLLEGE\SEM 5\Research Method\CarbonHardware\data\raw\carbonset\CarbonSet.csv`
Rows: 1320  
Columns (19): `Product`, `Type`, `Release Date`, `Process Size (nm)`, `TDP (W)`, `DieSizeValue`, `Die Size (mm^2)`, `Vendor`, `#dies`, `Avg Die Area`, `Emb_Carbon_Min`, `Ope_Carbon_Min`, `Tot_Carbon_Min`, `Emb_Carbon_Max`, `Ope_Carbon_Max`, `Tot_Carbon_Max`, `Emb_Carbon_Mean`, `Ope_Carbon_Mean`, `Tot_Carbon_Mean`
Duplicate rows: 17
Candidate targets: [{"column": "Emb_Carbon_Min", "matched_terms": ["emb carbon"], "status": "candidate only; verify definition and unit"}, {"column": "Emb_Carbon_Max", "matched_terms": ["emb carbon"], "status": "candidate only; verify definition and unit"}, {"column": "Emb_Carbon_Mean", "matched_terms": ["emb carbon"], "status": "candidate only; verify definition and unit"}]
- `Product`: dtype `str`, missing 0 (0.0%), unique 1272, units suggested by name: none
- `Type`: dtype `str`, missing 0 (0.0%), unique 2, units suggested by name: none
- `Release Date`: dtype `str`, missing 0 (0.0%), unique 389, units suggested by name: none
- `Process Size (nm)`: dtype `float64`, missing 0 (0.0%), unique 5, units suggested by name: nm
- `TDP (W)`: dtype `float64`, missing 0 (0.0%), unique 112, units suggested by name: none
- `DieSizeValue`: dtype `float64`, missing 0 (0.0%), unique 102, units suggested by name: none
- `Die Size (mm^2)`: dtype `str`, missing 0 (0.0%), unique 103, units suggested by name: none
- `Vendor`: dtype `str`, missing 0 (0.0%), unique 3, units suggested by name: none
- `#dies`: dtype `int64`, missing 0 (0.0%), unique 4, units suggested by name: none
- `Avg Die Area`: dtype `float64`, missing 0 (0.0%), unique 97, units suggested by name: none
- `Emb_Carbon_Min`: dtype `float64`, missing 0 (0.0%), unique 114, units suggested by name: none
- `Ope_Carbon_Min`: dtype `float64`, missing 0 (0.0%), unique 225, units suggested by name: none
- `Tot_Carbon_Min`: dtype `float64`, missing 0 (0.0%), unique 464, units suggested by name: none
- `Emb_Carbon_Max`: dtype `float64`, missing 0 (0.0%), unique 114, units suggested by name: none
- `Ope_Carbon_Max`: dtype `float64`, missing 0 (0.0%), unique 225, units suggested by name: none
- `Tot_Carbon_Max`: dtype `float64`, missing 0 (0.0%), unique 464, units suggested by name: none
- `Emb_Carbon_Mean`: dtype `float64`, missing 0 (0.0%), unique 114, units suggested by name: none
- `Ope_Carbon_Mean`: dtype `float64`, missing 0 (0.0%), unique 225, units suggested by name: none
- `Tot_Carbon_Mean`: dtype `float64`, missing 0 (0.0%), unique 464, units suggested by name: none
## environmental

Available local data: **False**
Limitation: No supported local CSV or Excel files were found.
