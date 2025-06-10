#!/bin/bash

# metadata
# assume single experiment (/sra) xml for now

# query every zebrafish transcriptomics ("TRANSCRIPTOMIC" tag is kinda bad doesn't work should be the LibrarySource property)

# esearch -db sra -query 'txid7955[Organism:noexp] ("TRANSCRIPTOMIC" OR "METATRANSCRIPTOMIC" OR "TRANSCRIPTOMIC SINGLE CELL")' | efetch -format xml > zf.xml

METADATAXML=${1:-zf.xml}
OUTDIR=${2:-intermediate}

# 0) Ensure the output directory exists
mkdir -p "$OUTDIR"

# …now you can safely write into $OUTDIR…
# e.g.
echo "Reading metadata from $METADATAXML, writing intermediates to $OUTDIR/"


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

## just run accession and alias
xtract -input "${METADATAXML}" -head "run_accession\trun_alias" -pattern RUN -def "NA" -tab "\t" -sep ";" -element RUN@accession RUN@alias >"${OUTDIR}/all_zf_runs_to_GSMids.tsv"
#all_zf_runs_to_GSMids

## study to GEO ids
## study info - was JUST USE all_zf_metadata_study.tsv and not all_zf_studies_to_GSEids but running this script first!
xtract -input "${METADATAXML}" -self -head "study_accession\tstudy_alias" \
         -pattern STUDY -def "NA" \
         -element STUDY@accession STUDY@alias >"${OUTDIR}/all_zf_studies_to_GSEids.tsv"

## now running python commands in zebrafish-metadata-rosetta.py - this didn't work initially, need to source conda first

echo "Now loading python for zebrafish-metadata-rosetta.py"
module load data.science

# need this line first: Load the conda setup (adjust path to your system)
#source /hpc/user_apps/data.science/miniconda3/etc/profile.d/conda.sh
## found via conda info - this is wrong
## source /hpc/apps/x86_64/anaconda/2021_09_16/pkgs/conda-4.12.0-py38h578d9bd_0/etc/profile.d/conda.sh
## try this module load data.science then echo $CONDA_EXE
## results in /hpc/apps/x86_64/anaconda/2021_09_16/bin/conda
## so source should be /hpc/apps/x86_64/anaconda/2021_09_16/etc/profile.d/conda.sh

# Then activate your env
#conda activate single-cell-base

if [ -f "/hpc/apps/x86_64/anaconda/2021_09_16/etc/profile.d/conda.sh" ]; then
    source /hpc/apps/x86_64/anaconda/2021_09_16/etc/profile.d/conda.sh
    conda activate single-cell-base
else
    echo "ERROR: Cannot find conda.sh"
    exit 1
fi


# Now run your script
chmod a+x zebrafish-metadata-rosetta.py
echo "Now running python commands in zebrafish-metadata-rosetta.py"
./zebrafish-metadata-rosetta.py


echo "Complete!!"
