# Metadata Collection & Parsing

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

## Step 4: Script to curate technology.

Setup & script:
```
module load anaconda
module load data.science
conda activate single-cell-base
module load ugrep
./metadata-annotate.py combine all_zf_metadata2_run.tsv all_zf_metadata2_sample.tsv all_zf_metadata2_experiment.tsv all_zf_metadata2_study.tsv
```
This step adds a curated technology column

## Step 5: Jupyter Notebook to curate tissue type & developmental stage.

```
metadata_curatingdevstagetissue.ipynb
```

Notebook creates curated calls for fine & coarse tissue and devstage (columns), also incorporating tech column from step 4
Outputs: 
```
all_zf_dates_devstage_tissue_tech_curated.tsv
all_zf_dates_devstage_tissue_tech_curated_rawcolumns.tsv
```
