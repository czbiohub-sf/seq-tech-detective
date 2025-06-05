#!/bin/bash

# metadata
# assume single experiment (/sra) xml for now

# query every zebrafish transcriptomics ("TRANSCRIPTOMIC" tag is kinda bad doesn't work should be the LibrarySource property)

# esearch -db sra -query 'txid7955[Organism:noexp] ("TRANSCRIPTOMIC" OR "METATRANSCRIPTOMIC" OR "TRANSCRIPTOMIC SINGLE CELL")' | efetch -format xml > zf.xml

METADATAXML=${1:-zf.xml}
OUTDIR=${2:-intermediate}

# xtract: whenever we change the tab format for key-value. we need to use -deq on the next output
# to eat a queuead field separator
## for attributes was -tab ";" -sep ":" and first changed to -tab ";" -sep "|"  but need to correct to -tab "|" -sep ":" 

## THE FOLLOWING SCRIPT IS TO PULL FIELDS TO CREATE A 'ROSETTA' KEY FILE TO LINK RUNS, EXPERIMENTS, SAMPLES, STUDIES, BIORPOJECTS, AND GEO IDS

xtract -input "${METADATAXML}" -self -head "run_accession\tstudy_accession" -pattern EXPERIMENT_PACKAGE -STUDYKEY STUDY@accession -def "NA" -unit RUN -tab "\n" -element RUN@accession,"&STUDYKEY" >"${OUTDIR}/all_zf_runs_tostudyID.tsv"
xtract -input "${METADATAXML}" -self -head "run_accession\tsample_accession" -pattern EXPERIMENT_PACKAGE -SAMPLEKEY SAMPLE@accession -def "NA" -unit RUN -tab "\n" -element RUN@accession,"&SAMPLEKEY" >"${OUTDIR}/all_zf_runs_tosample.tsv"
xtract -input "${METADATAXML}" -self -head "run_accession\texperiment_accession" -pattern EXPERIMENT_PACKAGE -EXPKEY EXPERIMENT@accession -def "NA" -unit RUN -tab "\n" -element RUN@accession,"&EXPKEY" >"${OUTDIR}/all_zf_runs_to_experiment.tsv"

xtract -input "${METADATAXML}" -self -head "study_accession\tbioproject\tbioprojects" \
         -pattern STUDY -def "NA" \
         -element STUDY@accession \
         -group STUDY -unit IDENTIFIERS/EXTERNAL_ID -if @namespace -equals "BioProject" -position first -element EXTERNAL_ID \
         -group STUDY -unless IDENTIFIERS/EXTERNAL_ID@namespace -contains "BioProject" -lbl "NA" \
         -group STUDY -unit IDENTIFIERS/EXTERNAL_ID -if @namespace -equals "BioProject" -sep ':' -tab ';' -element EXTERNAL_ID \
         -group STUDY -unless IDENTIFIERS/EXTERNAL_ID@namespace -contains "BioProject" -lbl "NA" >"${OUTDIR}/all_zf_studyID_tobioprojects.tsv"



## study info
## study info - JUST USE all_zf_metadata_study.tsv and not all_zf_studies_to_GSEids

# xtract -input "${METADATAXML}" -self -head "study_accession\tstudy_alias\tstudy_title\tstudy_type\tstudy_type_other\tstudy_abstract\tstudy_links\tstudy_attributes"  \
# -pattern STUDY -def "NA"  \
# -element STUDY@accession STUDY@alias  \
# -group DESCRIPTOR -def "NA" -element STUDY_TITLE STUDY_TYPE@existing_study_type STUDY_TYPE@new_study_type STUDY_ABSTRACT  \
# -group STUDY_LINKS -deq "\t" -unit XREF_LINK -tab ";" -sep ":" -element DB,ID  \
# -group STUDY -unless STUDY_LINKS/XREF_LINK -lbl "NA"  \
# -group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -tab ";" -sep ":" -element TAG,VALUE  \
# -group STUDY -unless STUDY_ATTRIBUTE -deq "\t" -lbl "NA" >"${OUTDIR}/all_zf_studies_to_GSEids.tsv"
#all_zf_studies_to_GSEids


# xtract -input "${METADATAXML}" -self -head "study_accession\tstudy_alias\tstudy_title\tstudy_type\tstudy_type_other\tstudy_abstract\tstudy_attributes\tstudy_PMIDs" \
# -pattern STUDY -def "NA" \
# -element STUDY@accession STUDY@alias \
# -group DESCRIPTOR -def "NA" -element STUDY_TITLE STUDY_TYPE@existing_study_type STUDY_TYPE@new_study_type STUDY_ABSTRACT \
# -group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -tab "|" -sep ":" -element TAG,VALUE \
# -group STUDY -unless STUDY_ATTRIBUTE -deq "\t" -lbl "NA" \
# -group STUDY_LINKS -deq "\t" -unit XREF_LINK -tab ";" -sep ":" -element DB,ID \
# >"${OUTDIR}/all_zf_metadata_study.tsv"


## just run accession and alias
xtract -input "${METADATAXML}" -head "run_accession\trun_alias" -pattern RUN -def "NA" -tab "\t" -sep ";" -element RUN@accession RUN@alias >"${OUTDIR}/all_zf_runs_to_GSMids.tsv"
#all_zf_runs_to_GSMids


# ALSO SEPARATE XML OF BIOPROJECT METADATA AND BIOPROJECT TSV VIA xtract

#./scripts/metadata-annotate.py combine ${OUTDIR}/all_zf_metadata_run.tsv ${OUTDIR}/all_zf_metadata_sample.tsv ${OUTDIR}/all_zf_metadata_experiment.tsv ${OUTDIR}/all_zf_metadata_study.tsv
