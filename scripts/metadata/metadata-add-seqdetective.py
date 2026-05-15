#!/usr/bin/env python3
# Join seq-detective metrics and judgements into a metadata TSV.
#
# Two optional input sources (at least one required):
#
#   Parquet (--parquet / positional arg):
#     mapping_rate_m1  → seqdetective.mate1.mapping_rate   (paired-end mate 1)
#     mapping_rate_m2  → seqdetective.mate2.mapping_rate   (paired-end mate 2; null for SE)
#     mapping_rate     → coalesced into seqdetective.mate1.mapping_rate (single-end)
#     (bioproject is dropped — already present in the metadata)
#
#   Judgement summary txt (--judgement):
#     Tab-separated, no header.  0-indexed columns:
#       col 0: run ID (with optional _subsample suffix)
#       col 3: seqdetective.judgement.mate1
#       col 4: seqdetective.judgement.mate2  (empty for single-end)
#       col 5: seqdetective.judgement.reason
#
# The run ID column is matched to run.accession (or accession) in the metadata;
# any _subsample suffix added by seq-detective is stripped first.
#
# Usage:
#   python metadata-add-seqdetective.py <metadata.tsv> <seqdetective.parquet>
#   python metadata-add-seqdetective.py <metadata.tsv> <seqdetective.parquet> \
#       --judgement seq-detective-judgement-summary-all.txt
#   python metadata-add-seqdetective.py <metadata.tsv> \
#       --judgement seq-detective-judgement-summary-all.txt
#   python metadata-add-seqdetective.py <metadata.tsv> <seqdetective.parquet> \
#       --cols seqdetective.mate1.mapping_rate,seqdetective.n_mates
#
# --cols: comma-separated seqdetective.* column names to keep (default: all).
#         Run with --list-cols to see available names.
#
# Output: <metadata_stem>_seqdetective.tsv

import sys
import argparse
import polars as pl
from pathlib import Path

# Columns with _m1/_m2 suffixes → mate1/mate2 output names
_M1_RENAME: dict[str, str] = {
    'mapping_rate_m1':     'seqdetective.mapping_rate.mate1',
    'nofeature_rate_m1':   'seqdetective.nofeature_rate.mate1',
    'sparsity_m1':         'seqdetective.sparsity.mate1',
    'pos_strand_rate_m1':  'seqdetective.pos_strand_rate.mate1',
    'readlen_m1':          'seqdetective.readlen.mate1',
}
_M2_RENAME: dict[str, str] = {
    'mapping_rate_m2':     'seqdetective.mapping_rate.mate2',
    'nofeature_rate_m2':   'seqdetective.nofeature_rate.mate2',
    'sparsity_m2':         'seqdetective.sparsity.mate2',
    'pos_strand_rate_m2':  'seqdetective.pos_strand_rate.mate2',
    'readlen_m2':          'seqdetective.readlen.mate2',
}
# Unsubscripted columns are single-end equivalents; coalesced into mate1.*
_SE_COALESCE: dict[str, str] = {
    'mapping_rate':    'seqdetective.mapping_rate.mate1',
    'nofeature_rate':  'seqdetective.nofeature_rate.mate1',
    'sparsity':        'seqdetective.sparsity.mate1',
    'pos_strand_rate': 'seqdetective.pos_strand_rate.mate1',
    'readlen':         'seqdetective.readlen.mate1',
}

_PARQUET_RENAME: dict[str, str] = {**_M1_RENAME, **_M2_RENAME, 'n_mates': 'seqdetective.n_mates'}

_JUDGEMENT_COLS = [
    'seqdetective.judgement.mate1',
    'seqdetective.judgement.mate2',
    'seqdetective.judgement.reason',
]

_STRIP_SUBSAMPLE = pl.col('id').str.replace(r'_subsample$', '', literal=False).alias('id')


def _load_parquet(path: str) -> pl.DataFrame:
    sd = pl.read_parquet(path)

    rename_present = {k: v for k, v in _PARQUET_RENAME.items() if k in sd.columns}
    known = set(_PARQUET_RENAME) | set(_SE_COALESCE) | {'id', 'bioproject'}
    unknown = [c for c in sd.columns if c not in known]
    if unknown:
        print(f'[warn] unrecognised parquet columns (kept as-is): {unknown}', file=sys.stderr)

    sd = sd.rename(rename_present)

    for se_col, mate1_col in _SE_COALESCE.items():
        if se_col in sd.columns:
            if mate1_col in sd.columns:
                sd = sd.with_columns(
                    pl.coalesce([pl.col(mate1_col), pl.col(se_col)]).alias(mate1_col)
                ).drop(se_col)
            else:
                sd = sd.rename({se_col: mate1_col})

    if 'bioproject' in sd.columns:
        sd = sd.drop('bioproject')

    sd = sd.with_columns(_STRIP_SUBSAMPLE)
    return sd


def _load_judgement(path: str) -> pl.DataFrame:
    # Tab-separated, no header; 6 columns (col 2 and col 4 may be empty for single-end)
    jdf = pl.read_csv(
        path, separator='\t', has_header=False,
        new_columns=['_id', '_f1', '_f2', '_j1', '_j2', '_reason'],
        infer_schema_length=0,
    )
    jdf = jdf.with_columns(
        pl.col('_id').str.replace(r'_subsample$', '', literal=False).alias('id'),
        pl.col('_j1').alias('seqdetective.judgement.mate1'),
        pl.col('_j2').replace('', None).alias('seqdetective.judgement.mate2'),
        pl.col('_reason').alias('seqdetective.judgement.reason'),
    ).select(['id'] + _JUDGEMENT_COLS)
    return jdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Join seq-detective metrics and/or judgements into a metadata TSV.')
    parser.add_argument('metadata',
                        help='Input metadata TSV')
    parser.add_argument('parquet', nargs='?', default=None,
                        help='seq-detective metrics parquet file (optional if --judgement given)')
    parser.add_argument('--judgement', default=None, metavar='TXT',
                        help='seq-detective judgement summary txt file')
    parser.add_argument('--cols', default=None,
                        help='Comma-separated seqdetective.* column names to include (default: all)')
    parser.add_argument('--list-cols', action='store_true',
                        help='Print available seqdetective.* column names and exit')
    parser.add_argument('--output', default=None,
                        help='Output path (default: <metadata_stem>_seqdetective.tsv)')
    args = parser.parse_args()

    if args.list_cols:
        all_cols = sorted(_PARQUET_RENAME.values()) + _JUDGEMENT_COLS
        print('\n'.join(all_cols))
        sys.exit(0)

    if not args.parquet and not args.judgement:
        parser.print_help(sys.stderr)
        sys.exit(1)

    meta = pl.read_csv(args.metadata, separator='\t', infer_schema_length=0)

    run_acc_col = next(
        (c for c in ('run.accession', 'accession') if c in meta.columns),
        None
    )
    if run_acc_col is None:
        print('ERROR: no accession column found in metadata', file=sys.stderr)
        sys.exit(1)

    # Build combined seqdetective frame, joining parquet + judgement on id
    sd: pl.DataFrame | None = None

    if args.parquet:
        sd = _load_parquet(args.parquet)

    if args.judgement:
        jdf = _load_judgement(args.judgement)
        sd = jdf if sd is None else sd.join(jdf, on='id', how='full', coalesce=True)

    sd_cols = [c for c in sd.columns if c != 'id']

    # Filter to requested columns
    if args.cols:
        requested = [c.strip() for c in args.cols.split(',')]
        unknown_req = [c for c in requested if c not in sd_cols]
        if unknown_req:
            print(f'[warn] requested columns not found (ignored): {unknown_req}', file=sys.stderr)
            print(f'[info] available: {sd_cols}', file=sys.stderr)
        sd_cols = [c for c in sd_cols if c in requested]
        if not sd_cols:
            print('ERROR: no valid columns to join', file=sys.stderr)
            sys.exit(1)

    sd_sub = sd.select(['id'] + sd_cols)

    # Drop pre-existing seqdetective columns for idempotency
    meta = meta.drop([c for c in sd_cols if c in meta.columns])

    result = meta.join(sd_sub, left_on=run_acc_col, right_on='id', how='left')

    out_path = args.output or (str(Path(args.metadata).with_suffix('')) + '_seqdetective.tsv')
    result.write_csv(out_path, separator='\t')

    n_matched = result.select(pl.col(sd_cols[0]).is_not_null().sum()).item() if sd_cols else 0
    print(f'[wrote] {out_path} ({len(result)} rows, {n_matched} with seqdetective data)',
          file=sys.stderr)


if __name__ == '__main__':
    main()
