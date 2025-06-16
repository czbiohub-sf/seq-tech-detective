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
metadata_join1 = metadata_rosetta5.join(metadata_run, on="run.accession", how="left")
metadata_join2 = metadata_join1.join(metadata_exp, on="experiment.accession", how="left")
metadata_join3 = metadata_join2.join(metadata_sample, on="sample.accession", how="left")
metadata_join4 = metadata_join3.join(metadata_study, on="study.accession", how="left")

# Save cleaned intermediate files
metadata_study.write_csv(f"{intermediate_folder}/all_zf_metadata2_study.tsv", separator="\t", null_value="NA")
metadata_sample.write_csv(f"{intermediate_folder}/all_zf_metadata2_sample.tsv", separator="\t", null_value="NA")
metadata_exp.write_csv(f"{intermediate_folder}/all_zf_metadata2_experiment.tsv", separator="\t", null_value="NA")
metadata_run.write_csv(f"{intermediate_folder}/all_zf_metadata2_run.tsv", separator="\t", null_value="NA")

# Load GEO metadata - note tricky rename here
metadata_GEO = read_tsv_with_na(f"{intermediate_folder}/all_zf_metadata_GEO.tsv").unique()
metadata_join4 = metadata_join4.rename({"GEO_sampleID": "GEOsample.accession"})
metadata_join4 = metadata_join4.join(metadata_GEO, on="GEOsample.accession", how="left")

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
if "run.pool_member" in metadata_join4.columns:
    pool_idx = metadata_join4.columns.index("run.pool_member")
    ordered_cols = metadata_join4.columns[:pool_idx + 1] + ["earliest_date"] + [
        c for c in metadata_join4.columns
        if c not in {"earliest_date"} and c not in metadata_join4.columns[:pool_idx + 1]
    ]
    metadata_join5 = metadata_join4.select(ordered_cols)
else:
    metadata_join5 = metadata_join4

# Patch missing bioproject values
metadata_join5 = metadata_join5.with_columns([
    pl.coalesce([pl.col("bioproject"), pl.col("study.accession")]).alias("bioprj")
])
metadata_join5 = metadata_join5.drop("bioproject")
metadata_join5 = metadata_join5.with_columns([
    pl.col("bioprj").str.replace_all("SRP00", "PRJXX").alias("bioproject")
])
metadata_join5 = metadata_join5.drop("bioprj")

# Sort by bioproject
metadata_join5 = metadata_join5.sort("bioproject")

print(f"NAs in date columns:")
print(f"")

for col in date_cols:
    print(f"{col}: {metadata_join5[col].null_count()}")    
    
# ADDING: splitting run.read_lengths of & run.base_counts


# Step 0: Helper for safe list indexing
def safe_get_list_index(df, list_col, new_col, index):
    values = df[list_col].to_list()
    extracted = [
        v[index] if isinstance(v, list) and len(v) > index else None
        for v in values
    ]
    return df.with_columns(pl.Series(new_col, extracted))

# Step 1: Start with splitting run.read_lengths
metadata_join5b = metadata_join5.with_columns([
    pl.col("run.read_lengths").cast(pl.Utf8).str.split(" ").alias("run_read_lengths_split")
])

# Step 2: Safely extract up to 4 read lengths
for i, name in enumerate(["run.r1_length", "run.r2_length", "run.r3_length", "run.r4_length"]):
    metadata_join5b = safe_get_list_index(metadata_join5b, "run_read_lengths_split", name, i)

# Step 3: Split run.base_counts and extract 5 fields
metadata_join5b = metadata_join5b.with_columns([
    pl.col("run.base_counts").cast(pl.Utf8).str.split(";").alias("run_base_counts_split")
])

for i, name in enumerate(["run.Acount", "run.Ccount", "run.Gcount", "run.Tcount", "run.Ncount"]):
    metadata_join5b = safe_get_list_index(metadata_join5b, "run_base_counts_split", name, i)

# Step 4: Clean prefixes from read lengths
metadata_join5b = metadata_join5b.with_columns([
    pl.col("run.r1_length").cast(pl.Utf8).str.replace("^0:", "").alias("run.r1_length"),
    pl.col("run.r2_length").cast(pl.Utf8).str.replace("^1:", "").alias("run.r2_length"),
    pl.col("run.r3_length").cast(pl.Utf8).str.replace("^2:", "").alias("run.r3_length"),
    pl.col("run.r4_length").cast(pl.Utf8).str.replace("^3:", "").alias("run.r4_length")
])

# Step 5: Clean base count prefixes
metadata_join5b = metadata_join5b.with_columns([
    pl.col("run.Acount").cast(pl.Utf8).str.replace("^A:", "").alias("run.Acount"),
    pl.col("run.Ccount").cast(pl.Utf8).str.replace("^C:", "").alias("run.Ccount"),
    pl.col("run.Gcount").cast(pl.Utf8).str.replace("^G:", "").alias("run.Gcount"),
    pl.col("run.Tcount").cast(pl.Utf8).str.replace("^T:", "").alias("run.Tcount"),
    pl.col("run.Ncount").cast(pl.Utf8).str.replace("^N:", "").alias("run.Ncount")
])

# Step 6: Convert specific malformed strings to null
metadata_join5b = metadata_join5b.with_columns([
    pl.when(pl.col("run.Acount").str.contains("^0:\\d+$")).then(None).otherwise(pl.col("run.Acount")).alias("run.Acount"),
    pl.when(pl.col("run.Ccount").str.contains("^1:\\d+$")).then(None).otherwise(pl.col("run.Ccount")).alias("run.Ccount"),
    pl.when(pl.col("run.Gcount").str.contains("^2:\\d+$")).then(None).otherwise(pl.col("run.Gcount")).alias("run.Gcount"),
    pl.when(pl.col("run.Tcount").str.contains("^3:\\d+$")).then(None).otherwise(pl.col("run.Tcount")).alias("run.Tcount"),
    pl.when(pl.col("run.Ncount").str.contains("^.:\\d+$")).then(None).otherwise(pl.col("run.Ncount")).alias("run.Ncount")
])

# Step 7: Convert all these columns to numeric
numeric_fields = [
    "run.r1_length", "run.r2_length", "run.r3_length", "run.r4_length",
    "run.Acount", "run.Ccount", "run.Gcount", "run.Tcount", "run.Ncount"
]

metadata_join5b = metadata_join5b.with_columns([
    pl.col(col).cast(pl.Float64).cast(pl.Int64) for col in numeric_fields
])


# (Optional cleanup: drop the temporary split lists if desired)
metadata_join5b = metadata_join5b.drop(["run_read_lengths_split", "run_base_counts_split"])


## replace 5 with 5b
metadata_join5 = metadata_join5b


desired_order = [
    "run.accession", "study.accession", "bioproject", "study.title", "sample.accession",
    "experiment.accession", "earliest_date", "run.title", "run.alias", "run.attributes",
    "experiment.title", "experiment.alias", "experiment.library_name", "experiment.design_description",
    "experiment.library_construction_protocol", "experiment.attributes", "sample.description",
    "sample.title", "sample.alias", "sample.attributes", "sample.centername", "run.filename",
    "run.semantic_name", "run.total_bases", "run.total_spots", "experiment.library_strategy",
    "experiment.library_source", "experiment.library_selection", "experiment.library_layout",
    "experiment.platform", "experiment.instrument_model", "experiment.spot_descriptor", "study.alias",
    "study.type", "study.abstract", "study.attributes", "study.PMIDs", "GEOsample.accession",
    "GEOsample.title", "GEOsample.dataprocessing", "GEOsample.source", "GEOsample.treatmentprotocol",
    "GEOsample.extractprotocol", "GEOsample.growthprotocol", "GEOsample.characteristics", "GEO_studyID",
    "GEO_sampleID_withrun", "run.read_lengths", "run.base_counts", "run.r1_length", "run.r2_length",
    "run.r3_length", "run.r4_length", "run.Acount", "run.Ccount", "run.Gcount", "run.Tcount", "run.Ncount",
    "run.experiment", "run.pool_member", "experiment.study_ref", "run.enafirstpublic_date",
    "run.enalastupdate_date", "run.lastSRAFile_date", "run.published_date", "run.SRAFile_date",
    "sample.enafirstpublic_date", "sample.enafirstpublic2_date", "sample.enalastupdate_date",
    "sample.enalastupdate2_date", "sample.insdcfirstpublic_date", "sample.insdclastupdate_date",
    "study.enafirstpublic_date", "study.enalastupdate_date", "GEOsample.submission_date",
    "GEOsample.release_date", "GEOsample.lastupdate_date"
]

# Only keep unique, existing columns in the requested order
seen = set()
final_columns = [col for col in desired_order if col in metadata_join5.columns and not (col in seen or seen.add(col))]
metadata_join5 = metadata_join5.select(final_columns)

# Write final result
metadata_join5.write_csv(f"{main_folder}/all_zf_datescurated_withGEO.tsv", separator="\t", null_value="NA")
