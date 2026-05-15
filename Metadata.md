# Metadata Collection & Parsing

# Environment

Steps 1–4 and 6–7 run in the same conda environment as seq-detective (see `environment.yml` in the repo root):
```
conda env create -f environment.yml
conda activate seq-tech-detective
```
Step 4 additionally requires `ugrep` to be available on `PATH` (HPC: `module load ugrep`).
Step 5 (tissue/devstage curation) is a Jupyter notebook and may use a different environment.

# Usage

## Step 0: Initial zebrafish NCBI run query + metadata download
Command would be:
```
esearch -db sra -query 'txid7955[Organism:noexp] ("TRANSCRIPTOMIC" OR "METATRANSCRIPTOMIC" OR "TRANSCRIPTOMIC SINGLE CELL")' | efetch -format xml > zf.xml
```
And would result in large zf.xml file.

Also adding Bioproject-specific XML for Submission info:
```
esearch -db bioproject -query 'txid7955[Organism:noexp]' | efetch -format xml > zf_bioproject.xml
```
Results in zf_bioproject.xml.


## Step 1: Script + processing for initial 'Rosetta' file to join intermediate metadata outputs
Script:
```
./zebrafish-metadata-rosetta.sh
```
The script runs initial NCBI `xtract` commands that create intermediate .tsv files. Running script also invokes Python commands in 
```
./zebrafish-metadata-rosetta.py
```
These result in a list of GEO IDs for GEO metadata extraction and a 'Rosetta' file `zf_rosetta.tsv` 

## Step 2: Script to separately download GEO metadata 
Usage:
```
./download_geo.sh all_zf_listofGSEids.tsv
```
This results in GEO metadata xml file used in final step.

## Step 3: Script to parse main intermediate metadata components.

Script:
```
./zebrafish-metadata.sh
```
The script runs more complete NCBI `xtract` commands that create intermediate .tsv files. Running the script similarly also invokes Python commands in 
```
./zebrafish-metadata-combining.py
```
These steps combine all of the intermediate .tsv files (as well as calculate an earliest date), resulting in the combined output
 `all_zf_datescurated_withGEO.tsv` 

## Step 4: Script to curate technology and sequencing metadata.

Setup & script:
```
conda activate seq-tech-detective
module load ugrep
./metadata-annotate.py fromcombined all_zf_datescurated_withGEO.tsv
```
Takes the combined TSV from step 3 directly, builds the per-level ugreppable files
internally, then runs annotation.  Alternatively, if you already have the ugreppable
files (e.g. from a previous `buildonly` run), you can call `combine` explicitly:
```
./metadata-annotate.py combine \
    all_zf_datescurated_withGEO_run_ugreppable.tsv \
    all_zf_datescurated_withGEO_sample_ugreppable.tsv \
    all_zf_datescurated_withGEO_exp_ugreppable.tsv \
    all_zf_datescurated_withGEO_study_ugreppable.tsv \
    all_zf_datescurated_withGEO_dataproc_ugreppable.tsv
```

Outputs:
```
full_metadata_combined.csv          — raw joined metadata (all columns)
annotated_metadata_combined.csv     — per-run resolved classification columns
```

Resolved columns added (beyond the original `technology`):
`tech_variant`, `tech_class`, `sc_or_bulk`, `assay_type`, `read_bias`,
`selection_class`, `prep_kit`, `layout`, `platform_family`,
`instrument_generation`, `instrument_model_slug`, `conflict_flags`

## Step 5: Jupyter Notebook to curate tissue type & developmental stage (Dec 2025 update).


```
metadata_75krun_curatingdevstagetissue_run121225.ipynb
```

Notebook creates curated calls for fine & coarse tissue and devstage (columns), also incorporating tech column from step 4

Outputs - 2 main & 3 checking unknowns
```
all_zf_dates_devstage_tissue_tech_curated.tsv
all_zf_dates_devstage_tissue_tech_curated_rawcolumns.tsv
all_zf_dates_devstage_tissue_tech_curated_unknown.tsv
all_zf_dates_devstage_tissue_tech_curated_unknowntissue.tsv
all_zf_dates_devstage_tissue_tech_curated_unknowndevstage.tsv
```

## Step 6: Join annotation columns into final curated metadata.

```
./metadata-join-annotations.py \
    all_zf_dates_devstage_tissue_tech_curated.tsv \
    annotated_metadata_combined.csv
```

Joins the resolved classification columns from step 4 into the final curated TSV.
Any pre-existing annotation columns are replaced (idempotent).

Output:
```
all_zf_dates_devstage_tissue_tech_curated_annotated.tsv
```

## Step 7: (Optional) Add seq-detective metrics.

If seq-detective output files are available, join their data into the metadata.
Both sources are optional but at least one must be provided:
```
./metadata-add-seqdetective.py \
    all_zf_dates_devstage_tissue_tech_curated_annotated.tsv \
    <path/to/seqdetective_metrics.parquet> \
    --judgement <path/to/seq-detective-judgement-summary-all.txt>
```

Adds columns prefixed `seqdetective.*`:
- `seqdetective.mate1.*` — mate 1 metrics; single-end run metrics are coalesced here
- `seqdetective.mate2.*` — mate 2 metrics (null for single-end runs)
- `seqdetective.n_mates` — 1 for single-end, 2 for paired-end
- `seqdetective.judgement.mate1` — per-mate judgement call (e.g. `B`)
- `seqdetective.judgement.mate2` — (null for single-end)
- `seqdetective.judgement.reason` — e.g. `usable mapping rate`

To include only a subset of columns:
```
./metadata-add-seqdetective.py ... \
    --cols seqdetective.mate1.mapping_rate,seqdetective.judgement.mate1,seqdetective.n_mates
```

List all available column names:
```
./metadata-add-seqdetective.py --list-cols
```

Output:
```
all_zf_dates_devstage_tissue_tech_curated_annotated_seqdetective.tsv
```
