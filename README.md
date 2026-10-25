# UMN PAN Dataset Figures

## UMN PAN Dataset: A Multimodal Clinical Dataset of Early Adversity, Placement History, and Prenatal Exposures in Adopted and Foster Care Children

**Christi R. P. Sullivan¹, Shelby Anderson¹, Logan Caola¹, Jonathan Lehman¹,
Taylor Rawstern¹, Jada Loleng¹, Jade Roghair¹, Audrey Houghton¹, Evan
Dastin-Van Rijn¹, Kimara Gustafson², Anita C. Randolph¹**

¹ Department of Psychiatry and Behavioral Sciences, University of Minnesota,
Minneapolis, MN, USA<br>
² Department of Pediatrics, University of Minnesota, Minneapolis, MN, USA

**Corresponding author:** Christi Sullivan · [perki322@umn.edu](mailto:perki322@umn.edu)

**Present address:** 2312 S. 6th St. Floor 2, Suite F-275, Minneapolis, MN 55454

This is the canonical repository for generating the figures and supplementary
tables for the UMN PAN Dataset paper. It contains the analysis scripts and
workflow. The de-identified BLOOM BUTTERFLY, PANDA, and COMPASS datasets are
publicly available through the University of Minnesota Digital Conservancy
(DRUM):

| Dataset | DOI |
| --- | --- |
| BLOOM BUTTERFLY | [10.13020/4FB1-7388](https://doi.org/10.13020/4FB1-7388) |
| BLOOM COMPASS | [10.13020/9PM0-3X73](https://doi.org/10.13020/9PM0-3X73) |
| BLOOM PANDA | [10.13020/S6XP-8Q21](https://doi.org/10.13020/S6XP-8Q21) |

The datasets are not distributed in this repository; download them from DRUM
(see [Inputs](#inputs)). Generated figures and tables are written to a local
`Figures/` folder that is excluded from Git. Review all results for disclosure
risk before sharing them.

## Set up

Use Python 3.11 or newer. From the repository root, create an environment and
install the pinned analysis dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `geopandas` and `shapely` packages are used to render the Figure 1 maps.
`Supplement B.py` also uses Pillow, which is installed as a Matplotlib
dependency.

## Inputs

Download the de-identified BLOOM datasets from DRUM using the DOIs above.
Create an `Input Data/` folder in the repository root (it is not included in
the repository) and place the downloaded files in it.

### BLOOM data

Place the files needed for the scripts you plan to run in `Input Data/`:

| File | Used for |
| --- | --- |
| `BLOOM_BUTTERFLY.csv` | Participant cohort and released demographic, adoption, placement, prenatal exposure, ACE, and supplementary-table fields; also used to validate cohort membership in COMPASS. |
| `BLOOM_COMPASS.xlsx` | Figure 5 clinical and laboratory data. The workbook must include the `Vitals`, `Problems`, `Diagnoses`, and `Labs` sheets. |
| `BLOOM_PANDA.xlsx` | Available from DRUM but not read by the scripts in this repository; it is not required to generate the figures or tables. |

**Cohort assumptions.** `Supplement B.py` asserts the expected cohort sizes of
the released data (2,720 valid-ID children and 1,706 eligible for the
age-at-adoption percentages) and that the ten history fields contain only
Yes/No values. If you use a different release or a modified file, the script
stops with an `AssertionError` instead of producing a table with different
denominators. The other scripts check data consistency (for example, that
categories sum to their denominators) but do not hard-code the cohort size.

The main BLOOM files can instead be stored together in another directory by
setting `BLOOM_DATA_DIR` to that directory. For example:

```bash
export BLOOM_DATA_DIR="/path/to/authorized/BLOOM/files"
```

The directory must contain `BLOOM_BUTTERFLY.csv` and `BLOOM_COMPASS.xlsx` for
all applicable scripts. This setting does not relocate the reference tables or
map assets described below, which ship with the repository.

### Reference tables

These public reference files are included in `References/`:

| Path | Used for |
| --- | --- |
| `References/icd9toicd10cmgem.csv` | First-mapping ICD-9 to ICD-10 conversion (CMS General Equivalence Mappings) for Figure 5 diagnoses. |
| `References/section111validicd10-jan2025_0.xlsx` | FY2025 ICD-10 short descriptions (CMS) used to label Figure 5 diagnoses. |
| `References/ethnicity_mapping.json` | Ordered ethnicity category rules used by Supplement B (see below). |

### Map assets

These map files are included in `Map Data/` and are used for the Figure 1
maps:

| Path | Used for |
| --- | --- |
| `Map Data/countries/ne_50m_admin_0_countries.*` | Country boundaries for the Figure 1 country map. Source: [Natural Earth](https://www.naturalearthdata.com/) "Admin 0 – Countries" (1:50m), public domain. |
| `Map Data/states/ne_110m_admin_1_states_provinces.*` | State/province boundaries for the Figure 1 state map. Source: [Natural Earth](https://www.naturalearthdata.com/) "Admin 1 – States, Provinces" (1:110m), public domain. |
| `Map Data/great_lakes.geojson` | Great Lakes overlay for the Figure 1 state map. |

Keep the shapefile components in each folder together.

### Supplement B ethnicity categories

`Supplement B.py` uses the category rules in
[`References/ethnicity_mapping.json`](./References/ethnicity_mapping.json).
This file preserves the original ethnicity categories and their rule order;
when a value occurs in more than one category, the first category takes
precedence. For example, Marshallese appears under both Asian and Pacific
Islander and is classified as Asian, matching the original table rules.

## Generate figures and tables

Run commands from the repository root. Each script writes to its corresponding
subdirectory under `Figures/`; it can be launched from another working
directory if its Python dependencies and inputs are available.

| Script | Output |
| --- | --- |
| `Demographic Figure.py` | Figure 1, including the country and state maps, under `Figures/Demographics/`. |
| `Placement Figure.py` | Figure 2 and placement aggregate counts under `Figures/Placement/`. |
| `Prenatal Substance Exposure Figure.py` | Figure 3 and exposure aggregate counts under `Figures/Prenatal Substance Exposure/`. |
| `ACE Figure.py` | Figure 4 and ACE field/distribution exports under `Figures/Adverse Childhood Experiences/`. |
| `Clinical Health Figure.py` | Figure 5, diagnosis/lab/head-circumference aggregates, and supporting audit files under `Figures/Clinical Health/`. |
| `Supplement A.py` | Supplement A table under `Figures/Supplement A/`. |
| `Supplement B.py` | Supplement B table and denominator outputs under `Figures/Supplement B/`. |

For example:

```bash
python "Demographic Figure.py"
python "Placement Figure.py"
python "Prenatal Substance Exposure Figure.py"
python "ACE Figure.py"
python "Clinical Health Figure.py"
python "Supplement A.py"
python "Supplement B.py"
```

The figure scripts generally produce a composite SVG and PNG with a transparent
background, plus a white-background PNG. Figures 1–5 also export separate panel
files under their `Individual Panels/` subdirectories. Supplement scripts
produce their table in SVG, PNG, and CSV formats. Aggregate CSVs and audit
files are written beside the corresponding figure or table.

The scripts create output folders as needed and replace files with matching
output names. They do not delete unrelated files already in those folders.

`bloom_aggregates.py` is an optional helper that rebuilds the aggregate CSV
exports for Figures 2 and 3 without rerendering their graphics. Normally, run
the corresponding figure scripts, which produce both the graphics and
aggregates.

## Outputs

### Figure and supplement folders

| Folder | Main generated files |
| --- | --- |
| `Figures/Demographics/` | Figure 1 composite SVG/PNGs and individual panels. |
| `Figures/Placement/` | Figure 2 composite SVG/PNGs, individual panels, and `placement_counts.csv`. |
| `Figures/Prenatal Substance Exposure/` | Figure 3 composite SVG/PNGs, individual panels, `exposure_counts.csv`, and `exposure_combinations.csv`. |
| `Figures/Adverse Childhood Experiences/` | Figure 4 composite SVG/PNGs, individual panels, `ace_counts.csv`, and `ace_distribution.csv`. |
| `Figures/Clinical Health/` | Figure 5 composite SVG/PNGs and individual panels; `icd10_chapter_counts.csv`, `mental_health_counts.csv`, `top_30_diagnoses.csv`, `code_labels.csv`, `diagnosis_preparation_audit.json`, `head_circumference_eligibility.csv`, `head_circumference_histogram.csv`, `lab_analyte_ranking.csv`, `abnormal_lab_counts.csv`, and `figure5_summary.json`. |
| `Figures/Supplement A/` | `Supplement A.svg`, PNGs, and `Supplement A.csv`. |
| `Figures/Supplement B/` | `Supplement B.svg`, PNGs, and `Supplement B.csv`. |

The Figure 5 CSV exports include chapter and mental-health counts,
top-diagnosis labels, ICD code labels, diagnosis preparation audit data,
head-circumference eligibility and histogram summaries, and laboratory
analyte-ranking and abnormal-result counts.

## Project files

- `bloom_data.py` centralizes input paths, cohort validation, COMPASS loading,
  diagnosis preparation, and head-circumference eligibility logic.
- `panel_exports.py` exports individual panels from composite figures.
- `References/ethnicity_mapping.json` supplies the ordered ethnicity categories
  used by Supplement B.
- `bloom_aggregates.py` can rebuild Figures 2 and 3 aggregate CSVs separately
  from rerendering their graphics.
- `requirements.txt` lists the Python dependencies and versions used for the
  figure scripts.

## Data handling and version control

The repository `.gitignore` excludes the `Input Data/` and `Figures/` folders,
CSV/Excel/JSON files (except those in `References/`), and generated images and
documents. The Python source, `README.md`, `requirements.txt`, `References/`,
and `Map Data/` are tracked. Ignoring files does not encrypt or otherwise
secure them.

Store only authorized data, follow applicable access controls, and review
generated figures and tables for disclosure risk before sharing.

## License

The code in this repository is released under the [MIT License](./LICENSE).
The BLOOM datasets are distributed separately through DRUM under their own
terms. The Natural Earth map data are in the public domain, and the ICD-9/ICD-10
reference tables are published by the Centers for Medicare & Medicaid Services.
