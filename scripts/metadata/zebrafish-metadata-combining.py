#!/usr/bin/env python3

##  using polars
import polars as pl
from datetime import datetime, date
import os

# Paths
main_folder = "."
intermediate_folder = "./intermediate"

# Helper to load TSVs treating "NA" as nulls
def read_tsv_with_na(path):
    return pl.read_csv(path, separator="\t", null_values=["NA"])

## function to force dates!!
def try_parse_date(x: str) -> date | None:
    if not x or x in {"NA", "null"}:
        return None
    x = x.strip()

    # Handle trailing 'Z' (e.g. 2015-02-10T14:39:50Z)
    if x.endswith("Z"):
        x = x[:-1]

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(x, fmt).date()
        except ValueError:
            continue
    return None


# Load main and intermediate metadata files
metadata_rosetta5 = read_tsv_with_na(f"{main_folder}/zf_rosetta.tsv")
metadata_study = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_study.tsv").unique()
metadata_sample = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_sample.tsv").unique()
metadata_exp = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_experiment.tsv")
metadata_run = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_run.tsv")

# Join all metadata layers
metadata_join1 = metadata_rosetta5.join(metadata_run, on="run_accession", how="left")
metadata_join2 = metadata_join1.join(metadata_exp, on="experiment_accession", how="left")
metadata_join3 = metadata_join2.join(metadata_sample, on="sample_accession", how="left")
metadata_join4 = metadata_join3.join(metadata_study, on="study_accession", how="left")

# Save cleaned intermediate files
metadata_study.write_csv(f"{intermediate_folder}/all_zf_metadata2_study.tsv", separator="\t", null_value="NA")
metadata_sample.write_csv(f"{intermediate_folder}/all_zf_metadata2_sample.tsv", separator="\t", null_value="NA")
metadata_exp.write_csv(f"{intermediate_folder}/all_zf_metadata2_experiment.tsv", separator="\t", null_value="NA")
metadata_run.write_csv(f"{intermediate_folder}/all_zf_metadata2_run.tsv", separator="\t", null_value="NA")

# Load GEO metadata
metadata_GEO = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_GEO.tsv").unique()
metadata_join4 = metadata_join4.rename({"GEO_sampleID": "GEO_accession"})
metadata_join4 = metadata_join4.join(metadata_GEO, on="GEO_accession", how="left")

# Drop columns where all values are null
all_na_cols = [
    col for col in metadata_join4.columns
    if metadata_join4.select(pl.col(col).drop_nulls().len()).item() == 0
]
print(f"Dropping all-NA columns: {all_na_cols}")
metadata_join4 = metadata_join4.select([col for col in metadata_join4.columns if col not in all_na_cols])

# Convert "date"-containing columns to proper Date type
date_cols = [c for c in metadata_join4.columns if "date" in c]

# Apply parser as object, then cast explicitly
for col in date_cols:
    print(f"Parsing {col}...")
    parsed_col = metadata_join4[col].cast(pl.Utf8).to_list()
    parsed_dates = [try_parse_date(x) for x in parsed_col]
    metadata_join4 = metadata_join4.with_columns([
        pl.Series(name=col, values=parsed_dates).cast(pl.Date)
    ])
    
    

# Compute earliest date
metadata_join4 = metadata_join4.with_columns([
    pl.min_horizontal([pl.col(col) for col in date_cols]).alias("earliest_date")
])


# Relocate date columns after study_PMIDs - skip
# pmid_idx = metadata_join4.columns.index("study_PMIDs")
# date_fields = [c for c in metadata_join4.columns if "date" in c and c != "earliest_date"]
# pre = metadata_join4.columns[:pmid_idx + 1]
# mid = date_fields
# post = [c for c in metadata_join4.columns if c not in pre + mid + ["earliest_date"]]
# metadata_join4 = metadata_join4.select(pre + mid + ["earliest_date"] + post)

# Move earliest_date after pool_member
if "pool_member" in metadata_join4.columns:
    pool_idx = metadata_join4.columns.index("pool_member")
    ordered_cols = metadata_join4.columns[:pool_idx + 1] + ["earliest_date"] + [
        c for c in metadata_join4.columns
        if c not in {"earliest_date"} and c not in metadata_join4.columns[:pool_idx + 1]
    ]
    metadata_join5 = metadata_join4.select(ordered_cols)
else:
    metadata_join5 = metadata_join4

# Patch missing bioproject values
metadata_join5 = metadata_join5.with_columns([
    pl.coalesce([pl.col("bioproject"), pl.col("study_accession")]).alias("bioprj")
])
metadata_join5 = metadata_join5.drop("bioproject")
metadata_join5 = metadata_join5.with_columns([
    pl.col("bioprj").str.replace_all("SRP00", "PRJXX").alias("bioproject")
])
metadata_join5 = metadata_join5.drop("bioprj")

# Relocate bioproject after study_accession - skip
# sa_idx = metadata_join5.columns.index("study_accession")
# reordered = metadata_join5.columns[:sa_idx + 1] + ["bioproject"] + [
#     c for c in metadata_join5.columns if c not in {"study_accession", "bioproject"}
# ]
# metadata_join5 = metadata_join5.select(reordered)

# Sort by bioproject
metadata_join5 = metadata_join5.sort("bioproject")

print(f"NAs in date columns:")
print(f"")

for col in date_cols:
    print(f"{col}: {metadata_join5[col].null_count()}")    
    
# Final desired column order (from R)
desired_order = [
    "run_accession", "study_accession", "bioproject", "study_title", "sample_accession",
    "experiment_accession", "earliest_date", "run_title", "run_alias", "run_attributes",
    "sample_description", "sample_title", "sample_centername", "sample_alias", "sample_attributes",
    "experiment_title", "experiment_alias", "experiment_library_name", "experiment_design_description",
    "experiment_library_construction_protocol", "experiment_attributes", "run_base:count",
    "run_filename", "run_read:length", "run_semantic_name", "total_bases", "total_spots",
    "experiment_library_strategy", "experiment_library_source", "experiment_library_selection",
    "experiment_library_layout", "experiment_platform", "experiment_instrument_model",
    "experiment_spot_descriptor", "study_alias", "study_type", "study_abstract", "study_attributes",
    "study_PMIDs", "GEO_accession", "GEO_title", "GEO_dataprocessing",
    "GEO_source", "GEO_treatmentprotocol", "GEO_extractprotocol", "GEO_growthprotocol",
    "GEO_characteristics", "GEO_studyID", "GEO_sampleID_withrun", "run_experiment",
    "pool_member", "study_ref", "run_enafirstpublic_date", "run_enalastupdate_date", "run_lastSRAFile_date",
    "run_published_date", "run_SRAFile_date", "sample_enafirstpublic_date",
    "sample_enafirstpublic2_date", "sample_enalastupdate_date", "sample_enalastupdate2_date",
    "sample_insdcfirstpublic_date", "sample_insdclastupdate_date", "study_enafirstpublic_date",
    "study_enalastupdate_date", "GEO_submission_date", "GEO_release_date", "GEO_lastupdate_date"
]

# Only keep unique, existing columns in the requested order
seen = set()
final_columns = [col for col in desired_order if col in metadata_join5.columns and not (col in seen or seen.add(col))]
metadata_join5 = metadata_join5.select(final_columns)

# Write final result
metadata_join5.write_csv(f"{main_folder}/all_zf_datescurated_withGEO.tsv", separator="\t", null_value="NA")

