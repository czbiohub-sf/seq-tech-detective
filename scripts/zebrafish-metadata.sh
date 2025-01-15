#!/bin/bash

# metadata
# assume single experiment (/sra) xml for now

# query every zebrafish transcriptomics ("TRANSCRIPTOMIC" tag is kinda bad doesn't work should be the LibrarySource property)

# esearch -db sra -query 'txid7955[Organism:noexp] ("TRANSCRIPTOMIC" OR "METATRANSCRIPTOMIC" OR "TRANSCRIPTOMIC SINGLE CELL")' | efetch -format xml > zf.xml

METADATAXML=${1:-zf.xml}
OUTDIR=${2:-intermediate}

# xtract: whenever we change the tab format for key-value. we need to use -deq on the next output
# to eat a queuead field separator

# RUN
xtract -input "${METADATAXML}" -head "accession\talias\texperiment\tpool_member\ttotal_spots\ttotal_bases\tpublished_date\ttitle\tspot_descriptor\tprocessing\tread:length\tbase:count\tfilename\tsemantic_name\trun_attributes" \
	-pattern RUN -def "N/A" -tab "\t" -sep ";" \
	-element RUN@accession RUN@alias \
	-element EXPERIMENT_REF@accession Pool/Member@accession \
	-element RUN@total_spots RUN@total_bases RUN@published \
	-element TITLE SPOT_DESCRIPTOR PROCESSING \
	-group Statistics -deq "\t" -unit Read -if Statistics/Read@index -tab " " -sep ":" -element @index,@average \
	-group RUN -unless Statistics/Read@index -lbl "N/A" \
	-group Bases -deq "\t" -unit Base -if Bases/Base@value -tab ";" -sep ":" -element @value,@count \
	-group RUN -unless Bases/Base@value -deq "\t" -lbl "N/A" \
	-group SRAFiles -deq "\t" -unit SRAFile -if SRAFile@supertype -equals "Original" -tab " " -element @filename \
	-group RUN -unless SRAFiles/SRAFile@supertype -equals "Original" -lbl "N/A" \
	-group SRAFiles -deq "\t" -unit SRAFile -if SRAFile@supertype -equals "Original" -tab " " -element @semantic_name \
	-group RUN -unless SRAFiles/SRAFile@supertype -equals "Original" -lbl "N/A" \
	-group RUN_ATTRIBUTES -deq "\t" -unit RUN_ATTRIBUTE -tab ";" -sep ":" -element TAG,VALUE \
	-group RUN -unless RUN_ATTRIBUTE -deq "\t" -lbl "N/A" \
	>"${OUTDIR}/all_zf_metadata_run.tsv"

# EXPERIMENT
xtract -input "${METADATAXML}" -self -head "accession\talias\tstudy\ttitle\tdesign_description\tlibrary_name\tlibrary_strategy\tlibrary_source\tlibrary_selection\tlibrary_layout\tlibrary_layout_tag\tplatform\tinstrument_model\tspot_descriptor\texperiment_attributes" \
	-pattern EXPERIMENT -def "N/A" \
	-element EXPERIMENT@accession EXPERIMENT@alias \
	-element STUDY_REF@accession \
	-element TITLE \
	-element DESIGN/DESIGN_DESCRIPTION \
	-group DESIGN/LIBRARY_DESCRIPTOR -def "N/A" -element LIBRARY_NAME LIBRARY_STRATEGY LIBRARY_SOURCE LIBRARY_SELECTION \
	-element LIBRARY_CONSTRUCTION_PROTOCOL \
	-block LIBRARY_LAYOUT/* -element ? \
	-group PLATFORM/* -element ? -element INSTRUMENT_MODEL \
	-group SPOT_DESCRIPTOR -element */? \
	-group EXPERIMENT -unless SPOT_DESCRIPTOR -lbl "N/A" \
	-group EXPERIMENT_ATTRIBUTES -deq "\t" -unit EXPERIMENT_ATTRIBUTE -tab ";" -sep ":" -element TAG,VALUE \
	>"${OUTDIR}/all_zf_metadata_experiment.tsv"

# SAMPLE
xtract -input "${METADATAXML}" -self -head "accession\talias\ttitle\tsample_attributes" \
	-pattern SAMPLE -def "N/A" \
	-element SAMPLE@accession SAMPLE@alias \
	-element TITLE \
	-group SAMPLE_ATTRIBUTES -deq "\t" -unit SAMPLE_ATTRIBUTE -tab ";" -sep ":" -element TAG,VALUE \
	>"${OUTDIR}/all_zf_metadata_sample.tsv"

# STUDY
xtract -input "${METADATAXML}" -self -head "accession\talias\ttitle\ttype\ttype_other\tabstract\tstudy_links\tstudy_attributes" \
	-pattern STUDY -def "N/A" \
	-element STUDY@accession STUDY@alias \
	-group DESCRIPTOR -def "N/A" -element STUDY_TITLE STUDY_TYPE@existing_study_type STUDY_TYPE@new_study_type STUDY_ABSTRACT \
	-group STUDY_LINKS -deq "\t" -unit XREF_LINK -tab ";" -sep ":" -element DB,ID \
	-group STUDY -unless STUDY_LINKS/XREF_LINK -lbl "N/A" \
	-group STUDY_ATTRIBUTES -deq "\t" -unit STUDY_ATTRIBUTE -tab ";" -sep ":" -element TAG,VALUE \
	>"${OUTDIR}/all_zf_metadata_study.tsv"

#./scripts/metadata-annotate.py combine ${OUTDIR}/all_zf_metadata_run.tsv ${OUTDIR}/all_zf_metadata_sample.tsv ${OUTDIR}/all_zf_metadata_experiment.tsv ${OUTDIR}/all_zf_metadata_study.tsv
