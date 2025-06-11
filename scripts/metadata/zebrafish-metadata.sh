#!/bin/bash
set -euo pipefail

# metadata
# assume single experiment (/sra) xml for now

# query every zebrafish transcriptomics ("TRANSCRIPTOMIC" tag is kinda bad doesn't work should be the LibrarySource property)

# esearch -db sra -query 'txid7955[Organism:noexp] ("TRANSCRIPTOMIC" OR "METATRANSCRIPTOMIC" OR "TRANSCRIPTOMIC SINGLE CELL")' | efetch -format xml > zf.xml

METADATAXML=${1:-zf.xml}
OUTDIR=${2:-intermediate}
GEOXML=${3:-all_geo_families_cleaned.xml}

# xtract: whenever we change the tab format for key-value. we need to use -deq on the next output
# to eat a queuead field separator
## for attributes was -tab ";" -sep ":" and first changed to -tab ";" -sep "|"  but need to correct to -tab "|" -sep ":" 

echo ""
echo "Reading metadata from $METADATAXML, writing intermediates to $OUTDIR/"

# RUN
xtract -input "${METADATAXML}" -head "run_accession\trun_alias\trun_experiment\tpool_member\ttotal_spots\ttotal_bases\trun_published_date\trun_title\trun_spot_descriptor\trun_processing\trun_read:length\trun_base:count\trun_SRAFile_date\trun_lastSRAFile_date\trun_filename\trun_semantic_name\trun_attributes\trun_enafirstpublic_date\trun_enalastupdate_date" \
	-pattern RUN -def "NA" -tab "\t" -sep ";" \
	-element RUN@accession RUN@alias \
	-element EXPERIMENT_REF@accession Pool/Member@accession \
	-element RUN@total_spots RUN@total_bases RUN@published \
	-element TITLE SPOT_DESCRIPTOR PROCESSING \
	-group Statistics -deq "\t" -unit Read -if Statistics/Read@index -tab " " -sep ":" -element @index,@average \
	-group RUN -unless Statistics/Read@index -lbl "NA" \
	-group Bases -deq "\t" -unit Base -if Bases/Base@value -tab ";" -sep ":" -element @value,@count \
	-group RUN -unless Bases/Base@value -deq "\t" -lbl "NA" \
	-group SRAFiles -deq "\t" -first SRAFile@date \
	-group RUN -unless SRAFiles/SRAFile@date -deq "\t" -lbl "NA" \
	-group SRAFiles -deq "\t" -last SRAFile@date \
	-group RUN -unless SRAFiles/SRAFile@date -deq "\t" -lbl "NA" \
	-group SRAFiles -deq "\t" -unit SRAFile -if SRAFile@supertype -equals "Original" -tab " " -element @filename \
	-group RUN -unless SRAFiles/SRAFile@supertype -equals "Original" -lbl "NA" \
	-group SRAFiles -deq "\t" -unit SRAFile -if SRAFile@supertype -equals "Original" -tab " " -element @semantic_name \
	-group RUN -unless SRAFiles/SRAFile@supertype -equals "Original" -lbl "NA" \
	-group RUN_ATTRIBUTES -deq "\t" -unit RUN_ATTRIBUTE -tab "|" -sep ":" -element TAG,VALUE \
	-group RUN -unless RUN_ATTRIBUTE -deq "\t" -lbl "NA" \
	-group RUN_ATTRIBUTES -deq "\t" -unit RUN_ATTRIBUTE -if RUN_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -element VALUE \
	-group RUN -unless RUN_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -lbl "NA" \
	-group RUN_ATTRIBUTES -deq "\t" -unit RUN_ATTRIBUTE -if RUN_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -element VALUE \
	-group RUN -unless RUN_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -lbl "NA" \
	>"${OUTDIR}/all_zf_metadata_run.tsv"

# EXPERIMENT
xtract -input "${METADATAXML}" -self -head "experiment_accession\texperiment_alias\tstudy_ref\texperiment_title\texperiment_design_description\texperiment_library_name\texperiment_library_strategy\texperiment_library_source\texperiment_library_selection\texperiment_library_construction_protocol\texperiment_library_layout\texperiment_platform\texperiment_instrument_model\texperiment_spot_descriptor\texperiment_attributes\texperiment_enafirstpublic_date" \
	-pattern EXPERIMENT -def "NA" \
	-element EXPERIMENT@accession EXPERIMENT@alias \
	-element STUDY_REF@accession \
	-element TITLE \
	-element DESIGN/DESIGN_DESCRIPTION \
	-group DESIGN/LIBRARY_DESCRIPTOR -def "NA" -element LIBRARY_NAME LIBRARY_STRATEGY LIBRARY_SOURCE LIBRARY_SELECTION \
	-element LIBRARY_CONSTRUCTION_PROTOCOL \
	-block LIBRARY_LAYOUT/* -element ? \
	-group PLATFORM/* -element ? -element INSTRUMENT_MODEL \
	-group SPOT_DESCRIPTOR -element */? \
	-group EXPERIMENT -unless SPOT_DESCRIPTOR -deq "\t" -lbl "NA" \
	-group EXPERIMENT_ATTRIBUTES -deq "\t" -unit EXPERIMENT_ATTRIBUTE -tab "|" -sep ":" -element TAG,VALUE \
	-group EXPERIMENT -unless EXPERIMENT_ATTRIBUTE -deq "\t" -lbl "NA" \
	-group EXPERIMENT_ATTRIBUTES -deq "\t" -unit EXPERIMENT_ATTRIBUTE -if EXPERIMENT_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -element VALUE \
	-group EXPERIMENT -unless EXPERIMENT_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -lbl "NA" \
	>"${OUTDIR}/all_zf_metadata_experiment.tsv"

# SAMPLE ENA first public ENA last update
xtract -input "${METADATAXML}" -self -head "sample_accession\tsample_alias\tsample_title\tsample_description\tsample_attributes\tsample_enafirstpublic_date\tsample_enalastupdate_date\tsample_enafirstpublic2_date\tsample_enalastupdate2_date\tsample_insdclastupdate_date\tsample_insdcfirstpublic_date\tsample_centername" \
	-pattern SAMPLE -def "NA" \
	-element SAMPLE@accession SAMPLE@alias \
	-element TITLE \
	-element DESCRIPTION \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -tab "|" -sep ":" -element TAG,VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE -deq "\t" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "ENA first public" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "ENA first public" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "ENA last update" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "ENA last update" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "INSDC last update" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "INSDC last update" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "INSDC first public" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "INSDC first public" -lbl "NA" \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -if SAMPLE_ATTRIBUTE/TAG -equals "INSDC center name" -element VALUE \
	-group SAMPLE -unless SAMPLE_ATTRIBUTE/TAG -equals "INSDC center name" -lbl "NA" \
	>"${OUTDIR}/all_zf_metadata_sample0.tsv"

# STUDY
xtract -input "${METADATAXML}" -self -head "study_accession\tstudy_alias\tstudy_title\tstudy_type\tstudy_type_other\tstudy_abstract\tstudy_attributes\tstudy_enafirstpublic_date\tstudy_enalastupdate_date\tstudy_PMIDs" \
	-pattern STUDY -def "NA" \
	-element STUDY@accession STUDY@alias \
	-group DESCRIPTOR -def "NA" -element STUDY_TITLE STUDY_TYPE@existing_study_type STUDY_TYPE@new_study_type STUDY_ABSTRACT \
	-group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -tab "|" -sep ":" -element TAG,VALUE \
	-group STUDY -unless STUDY_ATTRIBUTE -deq "\t" -lbl "NA" \
	-group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -if STUDY_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -element VALUE \
	-group STUDY -unless STUDY_ATTRIBUTE/TAG -equals "ENA-FIRST-PUBLIC" -lbl "NA" \
	-group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -if STUDY_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -element VALUE \
	-group STUDY -unless STUDY_ATTRIBUTE/TAG -equals "ENA-LAST-UPDATE" -lbl "NA" \
	-group STUDY_LINKS -deq "\t" -unit XREF_LINK -tab ";" -sep ":" -element DB,ID \
	>"${OUTDIR}/all_zf_metadata_study.tsv"
 
# ALSO 'ROSETTA' xtract COMMANDS
# ALSO SEPARATE XML OF BIOPROJECT METADATA AND BIOPROJECT TSV VIA xtract - no but pulling GEO below...

## need to trim a few NAs in extra 2 columns in sample.tsv - "${OUTDIR}/all_zf_metadata_sample.tsv"
cut -f1-12 "${OUTDIR}/all_zf_metadata_sample0.tsv" > "${OUTDIR}/all_zf_metadata_sample.tsv"

echo ""
echo "Reading GEO metadata from $GEOXML, writing intermediates to $OUTDIR/"


# GEO
xtract -input "${GEOXML}" -head "GEO_accession\tGEO_title\tGEO_dataprocessing\tGEO_submission_date\tGEO_release_date\tGEO_lastupdate_date\tGEO_source\tGEO_treatmentprotocol\tGEO_extractprotocol\tGEO_growthprotocol\tGEO_characteristics" \
        -pattern Sample -def "NA" -tab "\t" -sep ";" \
        -element Accession Title Data-Processing \
        -group Status -deq "\t" -def "NA" -element Submission-Date Release-Date Last-Update-Date \
        -group Channel -def "NA" -element Source Treatment-Protocol Extract-Protocol Growth-Protocol \
        -group Channel/Characteristics -tab "| " -sep ":" -element @tag,Characteristics -deq " | " \
	>"${OUTDIR}/all_zf_metadata_GEO.tsv"


## now running python commands in zebrafish-metadata-combining.py - first run module load anaconda
## these are CZB HPC-specific, BTW

echo "Now loading python for zebrafish-metadata-combining.py"
## try loading anaconda first??
module load anaconda
module load data.science

# now activate single-cell-base
#conda activate /hpc/user_apps/data.science/conda_envs/single-cell-base
conda activate single-cell-base

# Now run your script - make sure you have done this: chmod +x zebrafish-metadata-combining.py
echo "Now running python commands in zebrafish-metadata-combining.py"
./zebrafish-metadata-combining.py


echo "Complete!!"

## follow-up, for Y's technology curation script:
#./scripts/metadata-annotate.py combine ${OUTDIR}/all_zf_metadata_run.tsv ${OUTDIR}/all_zf_metadata_sample.tsv ${OUTDIR}/all_zf_metadata_experiment.tsv ${OUTDIR}/all_zf_metadata_study.tsv
