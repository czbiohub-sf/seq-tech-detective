#!/usr/bin/env python3
# Join resolved annotation columns from annotated_metadata_combined.csv
# into the final curated metadata TSV (e.g. all_zf_dates_devstage_tissue_tech_curated.tsv).
#
# Usage:
#   python metadata-join-annotations.py <final_metadata.tsv> <annotated_metadata_combined.csv>
#
# Output: <final_metadata_stem>_annotated.tsv
#
# Columns added (resolved summary only; no raw ugrep score columns):
#   technology, tech_variant, tech_class, sc_or_bulk, assay_type,
#   read_bias, selection_class, prep_kit, layout, platform_family,
#   instrument_generation, instrument_model_slug, conflict_flags

import sys
import polars as pl
from pathlib import Path

SUMMARY_COLS = [
    'technology', 'tech_variant', 'tech_class', 'sc_or_bulk',
    'assay_type', 'read_bias', 'selection_class', 'prep_kit',
    'layout', 'platform_family', 'instrument_generation',
    'instrument_model_slug', 'conflict_flags',
]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('final_metadata')
    parser.add_argument('annotated_csv')
    parser.add_argument('--output', default=None,
                        help='Output path (default: <final_metadata_stem>_annotated.tsv)')
    args = parser.parse_args()

    final_path, annot_path = args.final_metadata, args.annotated_csv

    final = pl.read_csv(final_path, separator='\t', infer_schema_length=0)
    annot = pl.read_csv(annot_path, infer_schema_length=0)

    # Detect run accession column in final metadata
    run_acc_col = next(
        (c for c in ('run.accession', 'accession') if c in final.columns),
        None
    )
    if run_acc_col is None:
        print(f'ERROR: no accession column found in {final_path}', file=sys.stderr)
        sys.exit(1)

    annot_set = set(annot.columns)
    present = [c for c in SUMMARY_COLS if c in annot_set]
    missing = [c for c in SUMMARY_COLS if c not in annot_set]
    if missing:
        print(f'[warn] missing columns in annotation file (skipped): {missing}', file=sys.stderr)

    annot_sub = annot.select(['accession'] + present)

    # Drop pre-existing annotation columns to make the join idempotent
    final = final.drop([c for c in present if c in final.columns])

    result = final.join(annot_sub, left_on=run_acc_col, right_on='accession', how='left')

    out_path = args.output or (str(Path(final_path).with_suffix('')) + '_annotated.tsv')
    result.write_csv(out_path, separator='\t')
    n_matched = result.select(pl.col('technology').is_not_null().sum()).item() if 'technology' in result.columns else 0
    print(f'[wrote] {out_path} ({len(result)} rows, {n_matched} with technology annotation)',
          file=sys.stderr)


if __name__ == '__main__':
    main()
