#!/usr/bin/env python3
# use polars to load our scan-species.sh csv (provided as an argument) and run the metadata-annotate function on it
# to match technology name pattern hits in the text
import polars as pl
import sys
import subprocess
import collections

class pattern:
    # a fuzzy match pattern runnable with ugrep
    # we use subprocess to run the command and capture the output
    # as matching line numbers, which are used as dataframe indices
    # usually runs:
    # ug -iPno --format=%n%~ <PAT> $file
    # ug -nZbest1 --format=%n%~ <PAT> $file

    def __init__(self, name, pattern, max_err):
        self.name = name
        self.pattern = pattern
        self.max_err = max_err
    
    ERR2ARG = {0: '-iPno', 1: '-inZbest1', 2: 'inZbest2'}
    def run(self, df, file):
        errarg = self.ERR2ARG[self.max_err]
        # run ugrep and get output in the form "linenumber\n" for each matching row
        cmd = ['ug', errarg, '--format=%n%~', self.pattern, file]
        output = subprocess.run(cmd, text=True, stdout=subprocess.PIPE)
        # caution! 1-indexed and header
        idxs = collections.Counter(int(line)-2 for line in output.stdout.split())
        return idxs

def metadata_annotate(file, keep_cols=[]):
    df = pl.read_csv(file, separator='\t', row_index_name='idx')

    # NAME, PATTERN, MAXERRORS
    patterns = [
        pattern('bulk', '(the |nano(particles)?[^a-z]* ?)?bulk', 0),
        pattern("10x1", '[^\t;]*(?<!/)10x[^\t;]*', 0),
        pattern('10x2', 'chromium', 1),
        pattern('10x3', 'Gel Bead Kit V3', 1),

        pattern('droncseq', 'dronc[-_ ]?seq', 1),
        pattern('dropseq', '\\bdrop[-_ ]?seq', 0),
        pattern('fluidigm', 'fluidigm', 1),
        pattern('indrops', 'indrops?', 1),
        #  other single-cell tech : 1 error
        pattern('marsseq', '\\bmars[-_ ]?seq', 1),
        pattern('matqseq', 'matq[-_ ]?seq', 1),
        pattern('quartzseq', 'quartz[-_ ]?seq', 1),
        pattern('smartseq1', 'smart[-_ ]?seq[23]', 1),
        pattern('smartseq2', 'smart template[- ]switching', 1),
        pattern('splitseq', 'split[-_ ]?seq', 1),
        pattern('superseq', 'super[-_ ]?seq', 1),
        pattern('microwellseq', 'microwell[-_ ]?seq', 1),
        # careful pattern 0 error
        pattern('scirnaseq', 'sci[-_ ]?rna[-_ ]?seq3?', 0),
        #pattern('smarter', '\\bsmarter\\b', 0),
        pattern('celseq', 'cel[-_]?seq', 0),
        pattern('cytoseq', 'cyto[-_ ]?seq', 0),
        pattern('seqwell', 'seq[-_ ]?well', 0),
        pattern('strtseq', 'strt[-_ ]?seq', 0),
        pattern('sortseq', 'sort[-_ ]?seq', 0),
        pattern('slamseq', '(sc)?slam[-_ ]?seq', 0),
        pattern('icell8', 'icell8', 0),
        pattern('iclip', 'iclip', 0),
        pattern('454', '\\b((LS|Roche )454|454 FLX)\\b', 0),
        pattern('scartrace', 'scartrace', 0), # based on sortseq, zebrafish specific?
        # generic "scRNA-seq" , 0 error, offlist: "[...fi]s[H] rnaseq"
        pattern('generic-scrnaseq1', 'sc[-_ ]?RNA[-_ ]?seq', 0),
        # generic "single-cell seq", 1 error, offlist: "single cell s[USpension]
        pattern('generic-scrnaseq2', 'single[-_ ]?cell[-_ ]?(RNA[-_ ])?seq(uencing)?', 1),
    ]
    
    # add a new column for each pattern, with the number of matches in the text
    blank = pl.Series("", [_ for _ in range(len(df))])
    df = df.with_columns(
        **{p.name: blank.replace_strict(p.run(df, file), default=0) for p in patterns}
    ).unique(subset=['accession'])
    # sum generic scrnaseq columns into a single column
    sum_cols = [['10x1', '10x2', '10x3'],
                ['generic-scrnaseq1', 'generic-scrnaseq2'],
                ['smartseq1', 'smartseq2']]
    df = df.with_columns(
        **{f"{cols[0][:-1]}": pl.sum_horizontal(cols) for cols in sum_cols}
    ).drop([col for cols in sum_cols for col in cols])
    # select the columns to keep, without sum_cols
    tech_cols = [p.name for p in patterns if p.name not in 
                 ['10x1', '10x2', '10x3', 'smartseq1', 'smartseq2', 'generic-scrnaseq1', 'generic-scrnaseq2']
                ]
    tech_cols = tech_cols + ['10x', 'smartseq', 'generic-scrnaseq']
    keep_cols = keep_cols + tech_cols
    df.write_csv(f"{file}-annotated.csv")
    print(f"{file}-annotated.csv")
    return df.select(keep_cols).shrink_to_fit(), tech_cols  #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python metadata-annotate.py <file>")
        sys.exit(1)
    
    if sys.argv[1] == "combine":
        run, tech_cols = metadata_annotate(sys.argv[2], keep_cols=['run_accession', 'run_experiment', 'pool_member', 'run_published_date', 'total_spots', 'run_read:length', 'run_semantic_name'])
        #add "run" suffix to tech columns
        run = run.rename({col: f"{col}_run" for col in tech_cols})
        samn, __ = metadata_annotate(sys.argv[3], keep_cols=['sample_accession'])
        samn = samn.rename({col: f"{col}_sample" for col in tech_cols})
        exp, __ = metadata_annotate(sys.argv[4], keep_cols=['experiment_accession', 'study_ref', 'experiment_library_source', 'experiment_platform', 'experiment_instrument_model'])
        exp = exp.rename({col: f"{col}_experiment" for col in tech_cols})
        study, __ = metadata_annotate(sys.argv[5], keep_cols=['study_accession'])
        study = study.rename({col: f"{col}_study" for col in tech_cols})
        # combine the dataframes
        df = run.join(exp, left_on='run_experiment', right_on='experiment_accession', how='left', suffix='_experiment').join(samn, left_on='pool_member', right_on='sample_accession', how='left', suffix='_sample').join(study, left_on='study_ref', right_on='study_accession', how='left', suffix='_study')
        #keep_library_source = ['TRANSCRIPTOMIC', 'METATRANSCRIPTOMIC', 'TRANSCRIPTOMIC_SINGLE_CELL']
        # create new weighted tech column
        df = df.with_columns(
            **{f"{col}": df[f"{col}_run"]*1000 + df[f"{col}_sample"]*100 + df[f"{col}_experiment"]*10 + df[f"{col}_study"] for col in tech_cols}
        ).drop([f"{col}_run" for col in tech_cols] + 
               [f"{col}_sample" for col in tech_cols] + 
               [f"{col}_experiment" for col in tech_cols] + 
               [f"{col}_study" for col in tech_cols]
            )
        tech_cols_no_generic = [col for col in tech_cols if col != 'generic-scrnaseq']
        tech_cols_yes_generic = tech_cols_no_generic + ['generic-scrnaseq-only']
        # create generic-scrnaseq-only column if generic-scrnaseq > 0 and all other tech columns are 0
        df.with_columns(
            (pl.when(
                (pl.col('generic-scrnaseq') > 0) & 
                (pl.sum_horizontal(tech_cols_no_generic) == 0)
                ).then(pl.col('generic-scrnaseq') + 1).otherwise(0)).alias('generic-scrnaseq-only')
        ).with_columns( # create a new column with the technology name using arg_max to get the column name with the highest value
            technology=pl.coalesce(
                pl.when(pl.max_horizontal(tech_cols_yes_generic) == 0)
                .then(pl.lit("unknown"))
                .when(pl.col(tech)==pl.max_horizontal(tech_cols_yes_generic))
                .then(pl.lit(tech))
                for tech in tech_cols_yes_generic
            )
        ).write_csv("all_metadata_combined.csv")
        print("all_metadata_combined.csv")
        # grab just accession and semantic_name columns
        df.select(['run_accession', 'run_semantic_name']).write_csv("accession_data_for_scan.csv", include_header=False)
        print("accession_data_for_scan.csv")
    else:
        for file in sys.argv[1:]:
            metadata_annotate(file)
