#!/usr/bin/env python3
# using pandas to replicate R commands to process - got this error
# ImportError: /lib64/libstdc++.so.6: version `GLIBCXX_3.4.29' not found (required by /hpc/user_apps/data.science/conda_envs/single-cell-base/lib/python3.10/site-packages/pandas/_libs/window/aggregations.cpython-310-x86_64-linux-gnu.so)

## second try using polars

import polars as pl
import os

# Define paths
input_folder = "./intermediate"
output_rosetta_file = "zf_rosetta.tsv"
output_gse_file = "all_zf_listofGSEids.tsv"

# Load data
metadata_runstostudy = pl.read_csv(f"{input_folder}/all_zf_runs_tostudyID.tsv", separator="\t")
metadata_studytoprj = pl.read_csv(f"{input_folder}/all_zf_studyID_tobioprojects.tsv", separator="\t")
metadata_runstosample = pl.read_csv(f"{input_folder}/all_zf_runs_tosample.tsv", separator="\t")
metadata_runstoexp = pl.read_csv(f"{input_folder}/all_zf_runs_to_experiment.tsv", separator="\t")

## adding new submittedby
metadata_runstosubmitter = pl.read_csv(f"{input_folder}/all_zf_runs_to_submitter.tsv", separator="\t")

# Remove 'bioprojects' if it exists and deduplicate
if 'bioprojects' in metadata_studytoprj.columns:
    metadata_studytoprj = metadata_studytoprj.drop('bioprojects')

metadata_studytoprj = metadata_studytoprj.unique()

# Left join: run to study -> study to project
metadata_rosetta1 = metadata_runstostudy.join(metadata_studytoprj, on="study.accession", how="left")

# Full joins with sample and experiment metadata
metadata_rosetta2 = metadata_rosetta1.join(metadata_runstosample, on="run.accession", how="left")

## adding new submittedby
metadata_rosetta2b = metadata_rosetta2.join(metadata_runstosubmitter, on="run.accession", how="left")

metadata_rosetta3 = metadata_rosetta2b.join(metadata_runstoexp, on="run.accession", how="left")

# Load and filter GSE metadata
metadata_studiestoGSEids = pl.read_csv(f"{input_folder}/all_zf_studies_to_GSEids.tsv", separator="\t")
metadata_studiestoGSEids = (
    metadata_studiestoGSEids
    .select(["study.accession", "study.alias"])
    .unique()
    .filter(pl.col("study.alias").str.contains("GSE"))
)

# Load and process GSM metadata
metadata_runstoGSMids = pl.read_csv(f"{input_folder}/all_zf_runs_to_GSMids.tsv", separator="\t")
metadata_runstoGSMids = (
    metadata_runstoGSMids
    .select(["run.accession", "run.alias"])
    .unique()
    .filter(pl.col("run.alias").str.contains("GSM"))
    .with_columns(
        pl.col("run.alias").str.split("_").list.get(0).alias("GEO_sampleID")
    )
)

# Join with rosetta
metadata_rosetta4 = metadata_rosetta3.join(metadata_studiestoGSEids, on="study.accession", how="left")
metadata_rosetta5 = metadata_rosetta4.join(metadata_runstoGSMids, on="run.accession", how="left")

# Rename columns
metadata_rosetta5 = metadata_rosetta5.rename({
    "run.alias": "GEO_sampleID_withrun",
    "study.alias": "GEO_studyID"
})

# Write rosetta to main folder
#metadata_rosetta5.write_csv(output_rosetta_file, separator="\t")
# Save rosetta table with "NA" for missing values
metadata_rosetta5.write_csv(output_rosetta_file, separator="\t", null_value="NA")

# Write distinct list of GSE IDs to main folder (no header)
metadata_GSEids = metadata_studiestoGSEids.select("study.alias").unique()
#metadata_GSEids.write_csv(output_gse_file, separator="\t", include_header=False)

# Save GSE ID list with "NA" (although likely none will be null here)
metadata_GSEids.write_csv(output_gse_file, separator="\t", include_header=False, null_value="NA")
