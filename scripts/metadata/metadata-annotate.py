#!/usr/bin/env python3
# metadata-annotate.py
# Standalone replacement for metadata-annotate.py.
#
# Adds to the existing technology classification:
#   - assay_type    (coarse: rna_seq / atac_seq / chip_seq / small_rna / other_genomics)
#   - sc_or_bulk    (sc / sc_generic / bulk / unknown, library_source + tech signals)
#   - layout        (paired / single / unknown, from library_layout_tag column)
#   - selection_class (poly_a / rrna_depletion / random_priming / small_rna / …)
#   - read_bias     (3prime / 5prime / full_length / unknown, from protocol free-text)
#   - stranded      (bool-like weighted score from protocol text)
#   - platform_family      (illumina / ont / pacbio / bgi / ion_torrent / legacy / element)
#   - instrument_generation (hiseq_era / novaseq_era / nextseq / miseq / ont / pacbio_* / …)
#   - instrument_model_slug (normalized model slug)
#
# Structured columns (platform, instrument_model, library_strategy, library_source,
# library_selection) are resolved via direct dict lookup — not ugrep — because they
# have <50 unique values.  Free-text columns (library_construction_protocol, titles,
# attributes) still use the split-and-ugrep strategy for performance.
#
# Weighting hierarchy (same as original):
#   run × 1000  |  sample × 100  |  experiment × 10  |  study × 1
# ugrep patterns are run on each source TSV independently, then combined.
#
# Usage (combine mode — most common):
#   python metadata-annotate.py combine \
#       <run.tsv> <sample.tsv> <experiment.tsv> <study.tsv>
#
# Usage (fromcombined mode — takes combined TSV directly):
#   python metadata-annotate.py fromcombined <all_zf_datescurated_withGEO.tsv>
#
# Usage (buildonly mode — build ugreppable files without annotation):
#   python metadata-annotate.py buildonly <all_zf_datescurated_withGEO.tsv>
#
# Outputs:
#   full_metadata_combined.csv         — raw joined metadata (all columns)
#   annotated_metadata_combined.csv    — final table with all classification columns

import sys
import subprocess
import collections
from pathlib import Path

import polars as pl


# ---------------------------------------------------------------------------
# ugrep-based fuzzy pattern class (preserves original split-and-ugrep strategy)
# ---------------------------------------------------------------------------

class pattern:
    """Run a ugrep pattern against a TSV file; returns a Counter of 0-based row indices."""
    ERR2ARG = {0: '-iPno', 1: '-inZbest1', 2: '-inZbest2'}

    def __init__(self, name: str, pat: str, max_err: int):
        self.name = name
        self.pattern = pat
        self.max_err = max_err

    def run(self, filepath: str) -> collections.Counter:
        errarg = self.ERR2ARG[self.max_err]
        cmd = ['ug', errarg, '--format=%n%~', self.pattern, filepath]
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        # output lines are 1-indexed and include the header row → subtract 2
        return collections.Counter(
            int(ln) - 2 for ln in result.stdout.split() if ln.strip().isdigit()
        )


# ---------------------------------------------------------------------------
# Direct lookup tables for structured columns
# ---------------------------------------------------------------------------

ASSAY_TYPE_MAP = {
    'RNA-Seq':        'rna_seq',
    'FL-cDNA':        'rna_seq',
    'ssRNA-seq':      'rna_seq',
    'ATAC-seq':       'atac_seq',
    'ChIP-Seq':       'chip_seq',
    'miRNA-Seq':      'small_rna',
    'ncRNA-Seq':      'small_rna',
    'RIP-Seq':        'rip_seq',
    'Bisulfite-Seq':  'other_genomics',
    'WGS':            'other_genomics',
    'WXS':            'other_genomics',
    'AMPLICON':       'other_genomics',
    'OTHER':          'other_genomics',
}

LIBRARY_SOURCE_MAP = {
    'TRANSCRIPTOMIC SINGLE CELL': 'sc',
    'TRANSCRIPTOMIC':             'bulk',
    'METATRANSCRIPTOMIC':         'metatranscriptomic',
}

# SRA platform field → platform family
PLATFORM_FAMILY_MAP = {
    'ILLUMINA':          'illumina',
    'OXFORD_NANOPORE':   'ont',
    'PACBIO_SMRT':       'pacbio',
    'BGISEQ':            'bgi',
    'DNBSEQ':            'bgi',
    'ION_TORRENT':       'ion_torrent',
    'ABI_SOLID':         'legacy',
    'LS454':             'legacy',
    'COMPLETE_GENOMICS': 'legacy',
    'ELEMENT':           'element',
    'VELA_DIAGNOSTICS':  'legacy',
}

# instrument_model → (platform_family, instrument_generation, model_slug)
INSTRUMENT_MODEL_MAP = {
    # 454
    '454 GS FLX':                    ('legacy',     'early',          '454_gs_flx'),
    '454 GS FLX Titanium':           ('legacy',     'early',          '454_gs_flx_titanium'),
    # SOLiD
    'AB 5500 Genetic Analyzer':      ('legacy',     'early',          'ab_5500'),
    'AB SOLiD 3 Plus System':        ('legacy',     'early',          'ab_solid_3_plus'),
    'AB SOLiD System 3.0':           ('legacy',     'early',          'ab_solid_3'),
    # BGI / MGI
    'BGISEQ-500':                    ('bgi',        'bgi',            'bgiseq_500'),
    'DNBSEQ-G400':                   ('bgi',        'bgi',            'dnbseq_g400'),
    'DNBSEQ-G50':                    ('bgi',        'bgi',            'dnbseq_g50'),
    'DNBSEQ-T7':                     ('bgi',        'bgi',            'dnbseq_t7'),
    'MGISEQ-2000RS':                 ('bgi',        'bgi',            'mgiseq_2000rs'),
    # Complete Genomics
    'Complete Genomics':             ('legacy',     'early',          'complete_genomics'),
    # Element
    'Element AVITI':                 ('element',    'element',        'element_aviti'),
    # Oxford Nanopore
    'GridION':                       ('ont',        'ont',            'gridion'),
    'MinION':                        ('ont',        'ont',            'minion'),
    'PromethION':                    ('ont',        'ont',            'promethion'),
    # Illumina — early / legacy
    'Illumina Genome Analyzer':      ('illumina',   'early_illumina', 'ga'),
    'Illumina Genome Analyzer II':   ('illumina',   'early_illumina', 'ga_ii'),
    'Illumina Genome Analyzer IIx':  ('illumina',   'early_illumina', 'ga_iix'),
    'Illumina HiScanSQ':             ('illumina',   'early_illumina', 'hiscansq'),
    # Illumina — HiSeq era
    'Illumina HiSeq 1000':           ('illumina',   'hiseq_era',      'hiseq_1000'),
    'Illumina HiSeq 1500':           ('illumina',   'hiseq_era',      'hiseq_1500'),
    'Illumina HiSeq 2000':           ('illumina',   'hiseq_era',      'hiseq_2000'),
    'Illumina HiSeq 2500':           ('illumina',   'hiseq_era',      'hiseq_2500'),
    'Illumina HiSeq 3000':           ('illumina',   'hiseq_era',      'hiseq_3000'),
    'Illumina HiSeq 4000':           ('illumina',   'hiseq_era',      'hiseq_4000'),
    'HiSeq X Five':                  ('illumina',   'hiseq_era',      'hiseq_x_five'),
    'HiSeq X Ten':                   ('illumina',   'hiseq_era',      'hiseq_x_ten'),
    'Illumina HiSeq X':              ('illumina',   'hiseq_era',      'hiseq_x'),
    'Illumina HiSeq X Ten':          ('illumina',   'hiseq_era',      'hiseq_x_ten'),
    # Illumina — benchtop
    'Illumina MiSeq':                ('illumina',   'miseq',          'miseq'),
    'Illumina MiniSeq':              ('illumina',   'miseq',          'miniseq'),
    'Illumina iSeq 100':             ('illumina',   'miseq',          'iseq_100'),
    # Illumina — NextSeq
    'NextSeq 500':                   ('illumina',   'nextseq',        'nextseq_500'),
    'NextSeq 550':                   ('illumina',   'nextseq',        'nextseq_550'),
    'NextSeq 2000':                  ('illumina',   'nextseq_v2',     'nextseq_2000'),
    # Illumina — NovaSeq
    'Illumina NovaSeq 6000':         ('illumina',   'novaseq_era',    'novaseq_6000'),
    'Illumina NovaSeq X':            ('illumina',   'novaseq_era',    'novaseq_x'),
    'Illumina NovaSeq X Plus':       ('illumina',   'novaseq_era',    'novaseq_x_plus'),
    # Ion Torrent
    'Ion Torrent PGM':               ('ion_torrent','ion_torrent',    'ion_pgm'),
    'Ion Torrent Proton':            ('ion_torrent','ion_torrent',    'ion_proton'),
    'Ion Torrent S5':                ('ion_torrent','ion_torrent',    'ion_s5'),
    # PacBio
    'PacBio RS':                     ('pacbio',     'pacbio_early',   'pacbio_rs'),
    'PacBio RS II':                  ('pacbio',     'pacbio_early',   'pacbio_rs_ii'),
    'Sequel':                        ('pacbio',     'pacbio_modern',  'sequel'),
    'Sequel II':                     ('pacbio',     'pacbio_modern',  'sequel_ii'),
    # Sentosa (Vela)
    'Sentosa SQ301':                 ('legacy',     'early',          'sentosa_sq301'),
}

LIBRARY_SELECTION_MAP = {
    'cDNA_oligo_dT':        'poly_a',
    'Oligo-dT':             'poly_a',
    'PolyA':                'poly_a',
    'cDNA_randomPriming':   'random_priming',
    'RANDOM':               'random_priming',
    'RANDOM PCR':           'random_priming',
    'PCR':                  'random_priming',
    'Inverse rRNA':         'rrna_depletion',
    'CAGE':                 'cage',
    'cDNA':                 'cdna_unspecified',
    'DNase':                'dnase',
    'other':                'other',
    'RACE':                 'other',
    'RT-PCR':               'other',
    'Reduced Representation': 'other',
    'size fractionation':   'size_fractionation',
    'unspecified':          'unknown',
}

# Technologies that imply single-cell (for sc_or_bulk fallback)
SC_TECH_NAMES = frozenset({
    '10x', 'marsseq', 'smartseq', 'dropseq', 'droncseq', 'celseq',
    'indrops', 'matqseq', 'quartzseq', 'splitseq', 'scirnaseq',
    'microwellseq', 'cytoseq', 'seqwell', 'fluidigm', 'icell8',
    'strtseq', 'sortseq', 'scartrace', 'scslamseq',
})

# Bulk-specific technology names (for conflict detection)
BULK_TECH_NAMES = frozenset({'bulk', 'detct', 'slamseq'})

# Tech → implied read bias (used in conflict checking)
TECH_IMPLIES_3PRIME  = frozenset({'10x', 'celseq', 'marsseq', 'dropseq', 'droncseq',
                                   'indrops', 'lexogen', 'quartzseq', 'cytoseq'})
TECH_IMPLIES_FULLENGTH = frozenset({'smartseq', 'fluidigm'})

# SC techs that produce paired-end (barcode+insert) reads
TECH_IMPLIES_PAIRED = frozenset({'10x', 'dropseq', 'droncseq', 'marsseq', 'celseq',
                                  'indrops', 'splitseq', 'scirnaseq'})

TECH_CLASS_MAP = {
    '10x':                  'single_cell_droplet',
    'dropseq':              'single_cell_droplet',
    'indrops':              'single_cell_droplet',
    'droncseq':             'single_cell_droplet',
    'smartseq':             'single_cell_plate',
    'fluidigm':             'single_cell_plate',
    'celseq':               'single_cell_plate',
    'marsseq':              'single_cell_plate',
    'quartzseq':            'single_cell_plate',
    'scirnaseq':            'single_cell_plate',
    'splitseq':             'single_cell_plate',
    'microwellseq':         'single_cell_plate',
    'strtseq':              'single_cell_plate',
    'cytoseq':              'single_cell_plate',
    'seqwell':              'single_cell_plate',
    'icell8':               'single_cell_plate',
    'matqseq':              'single_cell_plate',
    'superseq':             'single_cell_plate',
    'generic-scrnaseq-only':'single_cell_generic',
    'bulk':                 'bulk',
    'detct':                'bulk',
    'slamseq':              'bulk',
    'scslamseq':            'single_cell_plate',
    'iclip':                'clip',
    'scartrace':            'other_seq',
    '454':                  'other_seq',
    'unknown':              'unknown',
}


# ---------------------------------------------------------------------------
# Pattern lists
# ---------------------------------------------------------------------------

# Preserved from metadata-annotate.py with targeted fixes (see comments).
TECH_PATTERNS = [
    pattern('bulk',              r'\bbulk\b.{0,40}(?:rna|transcriptom|seq)|\btotal\s+rna\b.{0,30}librar', 1),
    # 10x1 was r'[^\t;]*(?<!/)10x[^\t;]*' — matched "10x PBS", "10x TBE", dilution
    # factors, etc.  Replaced with context-anchored pattern requiring nearby
    # 10x-Genomics-specific terms so reagent concentrations don't false-match.
    pattern('10x1',              r'\b10[xX]\b.{0,20}(?:master\s*mix|barcode)|\b10[xX]\b.{0,60}(?:genomics|chromium|single.cell|[Gg][Ee][Mm]s?|v[23]|gene.express|flex|multiome)|(?:chromium|genomics).{0,60}\b10[xX]\b', 0),
    pattern('10x2',              r'chromium',                                          1),
    pattern('10x3',              r'Gel Bead Kit V3',                                  1),
    pattern('droncseq',          r'dronc[-_ ]?seq',                                   1),
    pattern('dropseq',           r'(?<![Uu]nlike )(?<![Cc]ompared to )\bdrop[-_ ]?seq(?!\s+[Tt]ools)', 0),
    pattern('fluidigm',          r'fluidigm',                                          1),
    pattern('indrops',           r'indrops?',                                          1),
    pattern('marsseq',           r'\bmars[-_ ]?seq',                                   1),
    pattern('matqseq',           r'matq[-_ ]?seq',                                    1),
    pattern('quartzseq',         r'quartz[-_ ]?seq',                                  1),
    # smartseq: match versioned (v2/v3/v4) AND plain "Smart-Seq" / "SMARTSeq" without
    # a version number (used by Clontech Smart-Seq kits v1–v4).  "SMARTer" alone is
    # excluded here because SMARTer Ultra Low kits are also used for bulk low-input
    # RNA-seq; bias_fullength already scores those separately.
    pattern('smartseq1',         r'smart[-_ ]?seq[234]',                              1),
    pattern('smartseq2',         r'smart template[- ]switching',                      1),
    pattern('smartseq3',         r'SMARTSeq\s+v[._ ]?\d|clontech.{0,25}smart[-_ ]?seq(?!\s*ultra)', 0),
    pattern('smartseq4',         r'smart[-_ ]?seq\s*(?:TM|™)',                        0),
    pattern('smartseq5',         r'smart[-_ ]?seq\s*[®™]?\s*v[234]|SMART-Seq\s+v[234]', 1),
    pattern('detct',             r'\bdetct\b|DeTCT',                                  0),
    pattern('scslamseq',         r'\bsc[-_ ]?slam[-_ ]?seq\b',                        0),
    pattern('slamseq',           r'(?<![Ss][Cc][-_ ]?)\bslam[-_ ]?seq\b|4-thiouridine|s4U.{0,20}label',  0),
    pattern('splitseq',          r'split[-_ ]?seq',                                   1),
    pattern('superseq',          r'super[-_ ]?seq',                                   1),
    pattern('microwellseq',      r'microwell[-_ ]?seq',                               1),
    pattern('scirnaseq',         r'sci[-_ ]?rna[-_ ]?seq3?',                          0),
    pattern('celseq',            r'cel[-_]?seq',                                       0),
    pattern('cytoseq',           r'cyto[-_ ]?seq',                                    0),
    pattern('seqwell',           r'seq[-_ ]?well',                                    0),
    pattern('strtseq',           r'strt[-_ ]?seq',                                    0),
    pattern('sortseq',           r'sort[-_ ]?seq',                                    0),
    pattern('icell8',            r'icell8',                                            0),
    pattern('iclip',             r'iclip',                                             0),
    pattern('454',               r'\b((LS|Roche )454|454 FLX)\b',                     0),
    pattern('scartrace',         r'scartrace',                                         0),
    pattern('generic-scrnaseq1', r'sc[-_ ]?RNA[-_ ]?seq',                             0),
    pattern('generic-scrnaseq2', r'single[-_ ]?cell[-_ ]?(RNA[-_ ])?seq(uencing)?',   1),
    pattern('generic-scrnaseq3', r'scslam[-_ ]?seq',                                  0),
]

# New: read bias inferred from free-text protocol/design fields
BIAS_PATTERNS = [
    # 3′ bias: QuantSeq 3′, oligo-dT language, 3′ gene expression
    pattern('bias_3prime',   r"3[''ʼ].{0,30}(gene|express|end|fwd|forward)|quantseq.{0,20}(3|fwd|forward)|3prime", 0),
    # 5′ bias: VDJ, 5′ gene expression (rare in RNA-seq but present)
    pattern('bias_5prime',   r"5[''ʼ].{0,30}(gene|express|end|vdj)|vdj.{0,20}5[''ʼ]|five.{0,5}prime.{0,30}(end|capture)", 0),
    # Full-length: SMARTer, SMART-seq without explicit 3′ anchor, full-length cDNA.
    # Using 0 errors — err=1 risks "hull-length", "null-length", etc.
    pattern('bias_fullength',r'full.?length|whole.{0,15}transcript|SMARTer', 0),
    # Strandedness signals (scored separately, not mutually exclusive with bias)
    pattern('stranded',      r'strand.?specific|directional|\bstranded\b(?!.*un)', 0),
    pattern('unstranded',    r'unstranded|non.?stranded', 0),
]

# New: library selection hints from free-text (used to fill gaps when library_selection
# field is 'unspecified' or 'cDNA' without further detail)
SELECTION_HINT_PATTERNS = [
    # \b guards prevent "polyamine", "polyacrylamide", "polymer" from false-matching
    pattern('sel_polya_hint',    r'\bpoly[- _]?a\b|\bpolya\b|oligo.?[dD][tT]|mrna.*select|select.*mrna', 0),
    pattern('sel_ribozero_hint', r'ribo.?zero|rrna.depl|deplete.*ribo|inverse.rrna',   1),
    pattern('sel_random_hint',   r'random.*prim|random.*hexamer|whole.*transcr',        0),
    pattern('sel_smallrna_hint', r'small.?rna|\bmirna\b|microrna|\btrna\b|18.30.nt',   0),
]

# Aliases: multi-pattern groups that get summed into one column.
# Naming convention: group[0] stripped of trailing digit gives the alias name.
# e.g. ['10x1','10x2','10x3'] → '10x'.  ['lexogen1','lexogen2'] → 'lexogen'.
_TECH_ALIASES = [
    ['10x1', '10x2', '10x3'],
    ['generic-scrnaseq1', 'generic-scrnaseq2', 'generic-scrnaseq3'],
    ['smartseq1', 'smartseq2', 'smartseq3', 'smartseq4', 'smartseq5'],
]
_ALIAS_SOURCES = {col for group in _TECH_ALIASES for col in group}
_ALIAS_TARGETS  = [group[0].rstrip('0123456789') for group in _TECH_ALIASES]

KIT_PATTERNS = [
    pattern('kit_trueseq1',  r'\btrue?.?seq\b',                                    0),
    pattern('kit_trueseq2',  r'illumina.{0,30}(strand|total.rna|mrna.kit)',         1),
    pattern('kit_nebnext',   r'neb.?next',                                          0),
    pattern('kit_nextera',   r'\bnextera\b',                                        0),
    pattern('kit_lexogen1',  r'lexogen',                                             0),
    pattern('kit_lexogen2',  r'\bquant.?seq\b',                                     0),
    pattern('kit_ribozero',  r'ribo.?zero',                                         0),
    pattern('kit_smarter',   r'\bSMARTer\b',                                        0),
]

_KIT_ALIASES = [
    ['kit_trueseq1', 'kit_trueseq2'],   # → kit_trueseq
    ['kit_lexogen1', 'kit_lexogen2'],   # → kit_lexogen
]
_KIT_ALIAS_SOURCES = {col for group in _KIT_ALIASES for col in group}
_KIT_ALIAS_TARGETS  = [group[0].rstrip('0123456789') for group in _KIT_ALIASES]

ALL_PATTERNS = TECH_PATTERNS + KIT_PATTERNS + BIAS_PATTERNS + SELECTION_HINT_PATTERNS


def _canonical_cols() -> tuple[list[str], list[str], list[str]]:
    """Return (tech_cols, kit_cols, new_cols) after alias collapsing."""
    tech_cols = (
        [p.name for p in TECH_PATTERNS if p.name not in _ALIAS_SOURCES]
        + _ALIAS_TARGETS
    )
    kit_cols = (
        [p.name for p in KIT_PATTERNS if p.name not in _KIT_ALIAS_SOURCES]
        + _KIT_ALIAS_TARGETS
    )
    new_cols = [p.name for p in BIAS_PATTERNS + SELECTION_HINT_PATTERNS]
    return tech_cols, kit_cols, new_cols


# ---------------------------------------------------------------------------
# Per-file annotation
# ---------------------------------------------------------------------------

def _annotate_file(filepath: str, keep_cols: list[str]) -> pl.DataFrame:
    """Load TSV, run all ugrep patterns, collapse aliases, write -annotated.tsv."""
    df = pl.read_csv(filepath, separator='\t', infer_schema_length=0)

    blank = pl.Series('', list(range(len(df))))
    df = df.with_columns(
        **{p.name: blank.replace_strict(p.run(filepath), default=0) for p in ALL_PATTERNS}
    ).unique(subset=['accession'])

    # Collapse multi-pattern aliases (strip trailing digit: '10x1' → '10x', etc.)
    for group in _TECH_ALIASES + _KIT_ALIASES:
        alias = group[0][:-1]
        df = df.with_columns(
            pl.sum_horizontal([pl.col(c) for c in group]).alias(alias)
        ).drop(group)

    df.write_csv(f'{filepath}-annotated.tsv')
    print(f'[annotated] {filepath}-annotated.tsv', file=sys.stderr)

    tech_cols, kit_cols, new_cols = _canonical_cols()
    valid_keep = [c for c in keep_cols if c in df.columns]
    return df.select(valid_keep + tech_cols + kit_cols + new_cols)


# ---------------------------------------------------------------------------
# Direct lookup resolution (applied to the joined experiment-level data)
# ---------------------------------------------------------------------------

def _apply_structured_lookups(df: pl.DataFrame) -> pl.DataFrame:
    """Map structured SRA columns to output classification fields."""

    # assay_type from library_strategy
    strat_frame = pl.DataFrame({
        'library_strategy': list(ASSAY_TYPE_MAP),
        '_assay_type':      list(ASSAY_TYPE_MAP.values()),
    })
    df = df.join(strat_frame, on='library_strategy', how='left').with_columns(
        pl.col('_assay_type').fill_null('unknown').alias('assay_type')
    ).drop('_assay_type')

    # sc_or_bulk_src (preliminary; finalised later with tech signals)
    src_frame = pl.DataFrame({
        'library_source':    list(LIBRARY_SOURCE_MAP),
        '_sc_or_bulk_src':   list(LIBRARY_SOURCE_MAP.values()),
    })
    df = df.join(src_frame, on='library_source', how='left').with_columns(
        pl.col('_sc_or_bulk_src').fill_null('unknown').alias('sc_or_bulk_src')
    ).drop('_sc_or_bulk_src')

    # layout from library_layout_tag (the actual PAIRED/SINGLE tag element)
    # Note: in the experiment TSV produced by metadata.sh the column is 'library_layout_tag';
    # the preceding 'library_layout' column holds LIBRARY_CONSTRUCTION_PROTOCOL text.
    layout_col = 'library_layout_tag' if 'library_layout_tag' in df.columns else 'library_layout'
    if layout_col in df.columns:
        df = df.with_columns(
            pl.when(pl.col(layout_col).str.to_uppercase() == 'PAIRED').then(pl.lit('paired'))
            .when(pl.col(layout_col).str.to_uppercase() == 'SINGLE').then(pl.lit('single'))
            .otherwise(pl.lit('unknown'))
            .alias('layout')
        )
    else:
        df = df.with_columns(pl.lit('unknown').alias('layout'))

    # selection_class_src from library_selection
    sel_frame = pl.DataFrame({
        'library_selection':  list(LIBRARY_SELECTION_MAP),
        '_selection_src':     list(LIBRARY_SELECTION_MAP.values()),
    })
    df = df.join(sel_frame, on='library_selection', how='left').with_columns(
        pl.col('_selection_src').fill_null('unknown').alias('selection_class_src')
    ).drop('_selection_src')

    # Instrument fields from instrument_model
    if 'instrument_model' in df.columns:
        inst_frame = pl.DataFrame({
            'instrument_model':     list(INSTRUMENT_MODEL_MAP),
            '_platform_family':     [v[0] for v in INSTRUMENT_MODEL_MAP.values()],
            '_inst_gen':            [v[1] for v in INSTRUMENT_MODEL_MAP.values()],
            '_inst_slug':           [v[2] for v in INSTRUMENT_MODEL_MAP.values()],
        })
        df = df.join(inst_frame, on='instrument_model', how='left').with_columns(
            pl.col('_platform_family').fill_null('unknown').alias('platform_family'),
            pl.col('_inst_gen').fill_null('unknown').alias('instrument_generation'),
            pl.col('_inst_slug').fill_null('unknown').alias('instrument_model_slug'),
        ).drop(['_platform_family', '_inst_gen', '_inst_slug'])

        # Fallback: platform column for models not yet in the map
        if 'platform' in df.columns:
            plat_frame = pl.DataFrame({
                'platform':         list(PLATFORM_FAMILY_MAP),
                '_plat_family':     list(PLATFORM_FAMILY_MAP.values()),
            })
            df = df.join(plat_frame, on='platform', how='left').with_columns(
                pl.when(pl.col('platform_family') == 'unknown')
                .then(pl.col('_plat_family').fill_null('unknown'))
                .otherwise(pl.col('platform_family'))
                .alias('platform_family')
            ).drop('_plat_family')
    else:
        df = df.with_columns(
            pl.lit('unknown').alias('platform_family'),
            pl.lit('unknown').alias('instrument_generation'),
            pl.lit('unknown').alias('instrument_model_slug'),
        )

    return df


# ---------------------------------------------------------------------------
# Resolution: weighted scores → single labels
# ---------------------------------------------------------------------------

def _resolve_technology(df: pl.DataFrame, tech_cols: list[str]) -> pl.DataFrame:
    """Weighted arg-max → technology label (same logic as original script)."""
    no_generic = [c for c in tech_cols if c != 'generic-scrnaseq']
    with_generic_only = no_generic + ['generic-scrnaseq-only']

    df = df.with_columns(
        pl.when(
            (pl.col('generic-scrnaseq') > 0) &
            (pl.sum_horizontal([pl.col(c) for c in no_generic]) == 0)
        ).then(pl.col('generic-scrnaseq') + 1)
        .otherwise(0)
        .alias('generic-scrnaseq-only')
    )

    # SC priority: any named single-cell technology scoring ≥10 (experiment-level or
    # stronger) suppresses the bulk score before argmax.  Bulk signal is structurally
    # weak — it fires on study abstracts and extraction kit names that appear throughout
    # SC protocols.  A specific SC technology match at experiment level is a qualitatively
    # stronger signal and should win.
    _specific_sc = [c for c in no_generic if c in SC_TECH_NAMES]
    if _specific_sc and 'bulk' in df.columns:
        sc_signal = pl.sum_horizontal([pl.col(c).fill_null(0) for c in _specific_sc])
        df = df.with_columns(
            bulk=pl.when(sc_signal.ge(10)).then(pl.lit(0)).otherwise(pl.col('bulk'))
        )

    _max_score = pl.max_horizontal([pl.col(c) for c in with_generic_only])
    df = df.with_columns(
        technology=pl.coalesce(
            pl.when(_max_score == 0)
            .then(pl.lit('unknown'))
            .when(pl.col(tech) == _max_score)
            .then(pl.lit(tech))
            for tech in with_generic_only
        )
    )

    # Demote sortseq → celseq (sort_seq is a variant of CEL-seq2, not a peer technology)
    df = df.with_columns(
        tech_variant=pl.when(pl.col('technology') == 'sortseq')
                     .then(pl.lit('sort_seq'))
                     .otherwise(pl.lit(None)),
        technology=pl.when(pl.col('technology') == 'sortseq')
                   .then(pl.lit('celseq'))
                   .otherwise(pl.col('technology'))
    )
    return df


def _resolve_sc_or_bulk(df: pl.DataFrame, tech_cols: list[str]) -> pl.DataFrame:
    """Hierarchy: library_source SINGLE_CELL > specific sc tech > generic sc > bulk."""
    sc_cols = [c for c in tech_cols if c in SC_TECH_NAMES]
    sc_signal = (
        pl.sum_horizontal([pl.col(c) for c in sc_cols])
        if sc_cols else pl.lit(0)
    )

    df = df.with_columns(
        pl.when(pl.col('sc_or_bulk_src') == 'sc').then(pl.lit('sc'))
        .when(sc_signal > 0).then(pl.lit('sc'))
        .when(pl.col('generic-scrnaseq') > 0).then(pl.lit('sc_generic'))
        .when(pl.col('sc_or_bulk_src').is_in(['bulk', 'metatranscriptomic'])).then(pl.lit('bulk'))
        .otherwise(pl.lit('unknown'))
        .alias('sc_or_bulk')
    )
    return df


def _resolve_read_bias(df: pl.DataFrame) -> pl.DataFrame:
    """Hierarchy of specificity: 5′ > 3′ > full-length > unknown."""
    df = df.with_columns(
        pl.when(pl.col('bias_5prime') > 0).then(pl.lit('5prime'))
        .when(pl.col('bias_3prime') > 0).then(pl.lit('3prime'))
        .when(pl.col('bias_fullength') > 0).then(pl.lit('full_length'))
        .otherwise(pl.lit('unknown'))
        .alias('read_bias')
    )
    return df


def _resolve_selection(df: pl.DataFrame) -> pl.DataFrame:
    """Use structured value; fill 'unknown'/'cdna_unspecified' with protocol hints."""
    # 'other' is overridable: it's a catch-all with no specificity, so protocol
    # hints (poly_a, ribozero, random, small_rna) are more informative when present.
    overridable = ['unknown', 'cdna_unspecified', 'other']
    df = df.with_columns(
        pl.when(~pl.col('selection_class_src').is_in(overridable))
        .then(pl.col('selection_class_src'))
        .when(pl.col('sel_polya_hint') > 0).then(pl.lit('poly_a'))
        .when(pl.col('sel_ribozero_hint') > 0).then(pl.lit('rrna_depletion'))
        .when(pl.col('sel_random_hint') > 0).then(pl.lit('random_priming'))
        .when(pl.col('sel_smallrna_hint') > 0).then(pl.lit('small_rna'))
        .otherwise(pl.col('selection_class_src'))
        .alias('selection_class')
    )
    return df


def _resolve_prep_kit(df: pl.DataFrame, kit_cols: list[str]) -> pl.DataFrame:
    """Arg-max across kit columns → prep_kit label (strip 'kit_' prefix for display)."""
    kit_display = {c: c.removeprefix('kit_') for c in kit_cols}
    no_signal = pl.max_horizontal([pl.col(c) for c in kit_cols]) == 0
    return df.with_columns(
        prep_kit=pl.coalesce(
            pl.when(no_signal).then(pl.lit('unknown')),
            *(
                pl.when(pl.col(c) == pl.max_horizontal([pl.col(c) for c in kit_cols]))
                .then(pl.lit(kit_display[c]))
                for c in kit_cols
            )
        )
    )


def _resolve_tech_class(df: pl.DataFrame) -> pl.DataFrame:
    """Derive tech_class from resolved technology via TECH_CLASS_MAP."""
    tc_frame = pl.DataFrame({
        'technology': list(TECH_CLASS_MAP),
        '_tc':        list(TECH_CLASS_MAP.values()),
    })
    return df.join(tc_frame, on='technology', how='left').with_columns(
        pl.col('_tc').fill_null('unknown').alias('tech_class')
    ).drop('_tc')


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def _flag_conflicts(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add conflict_flags column: pipe-separated names of all detected signal
    disagreements.  Empty string means no conflicts found.
    """
    sc_tech_list   = sorted(SC_TECH_NAMES)
    bulk_tech_list = sorted(BULK_TECH_NAMES)
    prime3_list    = sorted(TECH_IMPLIES_3PRIME)
    fullength_list = sorted(TECH_IMPLIES_FULLENGTH)
    paired_list    = sorted(TECH_IMPLIES_PAIRED)

    is_sc_tech   = pl.col('technology').is_in(sc_tech_list)
    is_bulk_tech = pl.col('technology').is_in(bulk_tech_list)
    tech_known   = pl.col('technology') != 'unknown'

    flag_conditions: list[tuple[str, pl.Expr]] = [
        ('sc_tech|bulk_source',
         is_sc_tech & (pl.col('sc_or_bulk_src') == 'bulk')),

        ('sc_source|no_sc_tech',
         (pl.col('sc_or_bulk_src') == 'sc') & ~is_sc_tech & tech_known),

        ('bulk_tech|sc_source',
         is_bulk_tech & (pl.col('sc_or_bulk_src') == 'sc')),

        ('tech_3prime|fullength_bias',
         pl.col('technology').is_in(prime3_list) &
         (pl.col('read_bias') == 'full_length')),

        ('tech_fullength|3prime_bias',
         pl.col('technology').is_in(fullength_list) &
         (pl.col('read_bias') == '3prime')),

        ('paired_tech|single_layout',
         pl.col('technology').is_in(paired_list) &
         (pl.col('layout') == 'single')),

        ('sc_tech|rrna_depletion',
         is_sc_tech & (pl.col('selection_class') == 'rrna_depletion')),

        ('polya_selection|fullength_bias',
         (pl.col('selection_class') == 'poly_a') &
         (pl.col('read_bias') == 'full_length')),

        ('non_rna_assay|rna_source',
         ~pl.col('assay_type').is_in(['rna_seq', 'unknown']) &
         pl.col('sc_or_bulk_src').is_in(['sc', 'bulk'])),

        ('metatranscriptomic_source',
         pl.col('sc_or_bulk_src') == 'metatranscriptomic'),
    ]

    flag_exprs = [
        pl.when(cond).then(pl.lit(name)).otherwise(pl.lit(None))
        for name, cond in flag_conditions
    ]
    return df.with_columns(
        pl.concat_str(flag_exprs, separator='|', ignore_nulls=True)
        .alias('conflict_flags')
    )


# ---------------------------------------------------------------------------
# Build fast-ugreppable files from a single combined TSV
# ---------------------------------------------------------------------------

def _col(combined: str, out: str) -> tuple[str, str]:
    return (combined, out)


_RUN_COLS = [
    _col('run.accession',      'accession'),
    _col('run.experiment',     'experiment'),
    _col('run.pool_member',    'pool_member'),
    _col('run.published_date', 'published_date'),
    _col('run.total_spots',    'total_spots'),
    _col('run.semantic_name',  'semantic_name'),
    _col('run.title',          'title'),
    _col('run.alias',          'alias'),
    _col('run.attributes',     'attributes'),
]

_EXP_COLS = [
    _col('experiment.accession',                    'accession'),
    _col('experiment.study_ref',                    'study'),
    _col('experiment.library_strategy',             'library_strategy'),
    _col('experiment.library_source',               'library_source'),
    _col('experiment.library_selection',            'library_selection'),
    _col('experiment.library_layout',               'library_layout_tag'),
    _col('experiment.platform',                     'platform'),
    _col('experiment.instrument_model',             'instrument_model'),
    _col('experiment.title',                        'title'),
    _col('experiment.alias',                        'alias'),
    _col('experiment.library_name',                 'library_name'),
    _col('experiment.design_description',           'design_description'),
    _col('experiment.library_construction_protocol','library_construction_protocol'),
    _col('experiment.attributes',                   'attributes'),
]

_SAMPLE_COLS = [
    _col('sample.accession',            'accession'),
    _col('sample.title',                'title'),
    _col('sample.alias',                'alias'),
    _col('sample.description',          'description'),
    _col('sample.attributes',           'attributes'),
    _col('GEOsample.source',            'geo_source'),
    _col('GEOsample.treatmentprotocol', 'geo_treatmentprotocol'),
    _col('GEOsample.extractprotocol',   'geo_extractprotocol'),
    _col('GEOsample.growthprotocol',    'geo_growthprotocol'),
    _col('GEOsample.characteristics',   'geo_characteristics'),
]

_DATAPROC_COLS = [
    _col('sample.accession',         'accession'),
    _col('GEOsample.dataprocessing', 'geo_dataprocessing'),
]

_STUDY_COLS = [
    _col('study.accession',  'accession'),
    _col('study.title',      'title'),
    _col('study.abstract',   'abstract'),
    _col('study.attributes', 'attributes'),
]


def build_ugreppable_files(combined_tsv: str) -> tuple[str, str, str, str, str]:
    """
    Extract 5 compact per-level TSVs from a single combined metadata TSV
    (e.g. all_zf_datescurated_withGEO.tsv).

    Returns (run_tsv, sample_tsv, exp_tsv, study_tsv, dataproc_tsv) paths.
    Files are written next to the combined TSV.
    """
    base = Path(combined_tsv).with_suffix('')
    out_run      = str(base) + '_run_ugreppable.tsv'
    out_exp      = str(base) + '_exp_ugreppable.tsv'
    out_sample   = str(base) + '_sample_ugreppable.tsv'
    out_study    = str(base) + '_study_ugreppable.tsv'
    out_dataproc = str(base) + '_dataproc_ugreppable.tsv'

    df = pl.read_csv(combined_tsv, separator='\t', infer_schema_length=0)

    def _extract(col_spec: list[tuple[str, str]], dedup_col: str, out_path: str) -> None:
        present = [(src, dst) for src, dst in col_spec if src in df.columns]
        missing = [src for src, _ in col_spec if src not in df.columns]
        if missing:
            print(f'[build_ugreppable] {out_path}: skipping missing columns: {missing}', file=sys.stderr)
        src_cols, dst_cols = zip(*present)
        sub = df.select(list(src_cols)).rename(dict(zip(src_cols, dst_cols)))
        sub = sub.unique(subset=[dedup_col])
        sub.write_csv(out_path, separator='\t')
        print(f'[build_ugreppable] wrote {out_path} ({len(sub)} rows)', file=sys.stderr)

    _extract(_RUN_COLS,      'accession', out_run)
    _extract(_EXP_COLS,      'accession', out_exp)
    _extract(_SAMPLE_COLS,   'accession', out_sample)
    _extract(_STUDY_COLS,    'accession', out_study)
    _extract(_DATAPROC_COLS, 'accession', out_dataproc)

    return out_run, out_sample, out_exp, out_study, out_dataproc


# ---------------------------------------------------------------------------
# Combine mode
# ---------------------------------------------------------------------------

def combine(run_file: str, sample_file: str, exp_file: str, study_file: str,
            dataproc_file: str | None = None) -> None:
    tech_cols, kit_cols, new_cols = _canonical_cols()
    all_scored = tech_cols + kit_cols + new_cols

    # 1. Full joined metadata (raw, for downstream use)
    run_raw    = pl.read_csv(run_file,    separator='\t', infer_schema_length=0).unique(subset=['accession'])
    sample_raw = pl.read_csv(sample_file, separator='\t', infer_schema_length=0).unique(subset=['accession'])
    exp_raw    = pl.read_csv(exp_file,    separator='\t', infer_schema_length=0).unique(subset=['accession'])
    study_raw  = pl.read_csv(study_file,  separator='\t', infer_schema_length=0).unique(subset=['accession'])

    full = (
        run_raw
        .join(exp_raw,    left_on='experiment', right_on='accession', how='left', suffix='_exp')
        .join(sample_raw, left_on='pool_member', right_on='accession', how='left', suffix='_sample')
        .join(study_raw,  left_on='study',       right_on='accession', how='left', suffix='_study')
    )
    full.write_csv('full_metadata_combined.csv')
    print('[wrote] full_metadata_combined.csv', file=sys.stderr)
    del full, run_raw, sample_raw, study_raw

    # 2. Annotate each source TSV with ugrep patterns
    exp_keep = [
        'accession', 'study',
        'library_strategy', 'library_source', 'library_selection',
        'library_layout', 'library_layout_tag',
        'platform', 'instrument_model',
    ]
    exp_keep = [c for c in exp_keep if c in exp_raw.columns]
    del exp_raw

    run_ann    = _annotate_file(run_file,    keep_cols=['accession', 'experiment', 'pool_member',
                                                         'published_date', 'total_spots',
                                                         'read:length', 'semantic_name'])
    sample_ann = _annotate_file(sample_file, keep_cols=['accession'])
    exp_ann    = _annotate_file(exp_file,    keep_cols=exp_keep)
    study_ann  = _annotate_file(study_file,  keep_cols=['accession'])
    if dataproc_file is not None:
        dataproc_ann = _annotate_file(dataproc_file, keep_cols=['accession'])
    else:
        dataproc_ann = None

    # 3. Rename scored columns with source suffix
    run_ann    = run_ann.rename(   {c: f'{c}_run'        for c in all_scored})
    sample_ann = sample_ann.rename({c: f'{c}_sample'     for c in all_scored})
    exp_ann    = exp_ann.rename(   {c: f'{c}_experiment' for c in all_scored})
    study_ann  = study_ann.rename( {c: f'{c}_study'      for c in all_scored})
    if dataproc_ann is not None:
        dataproc_ann = dataproc_ann.rename({c: f'{c}_dataproc' for c in all_scored})

    # 4. Join annotated sources
    df = (
        run_ann
        .join(exp_ann,    left_on='experiment', right_on='accession', how='left')
        .join(sample_ann, left_on='pool_member', right_on='accession', how='left', suffix='_s')
        .join(study_ann,  left_on='study',       right_on='accession', how='left', suffix='_st')
    )
    if dataproc_ann is not None:
        df = df.join(dataproc_ann, left_on='pool_member', right_on='accession', how='left', suffix='_dp')

    # 5. Apply source weighting to produce combined scored columns
    active_srcs = ['run', 'sample', 'experiment', 'study']
    if dataproc_ann is not None:
        active_srcs.append('dataproc')
    source_cols_to_drop = [
        f'{col}_{src}'
        for col in all_scored
        for src in active_srcs
        if f'{col}_{src}' in df.columns
    ]

    def _dataproc_term(col: str) -> pl.Expr:
        if dataproc_ann is not None and f'{col}_dataproc' in df.columns:
            return pl.col(f'{col}_dataproc').fill_null(0) * 10
        return pl.lit(0)

    df = df.with_columns(**{
        col: (
            pl.col(f'{col}_run').fill_null(0)        * 1000 +
            pl.col(f'{col}_sample').fill_null(0)     * 100  +
            pl.col(f'{col}_experiment').fill_null(0) * 10   +
            pl.col(f'{col}_study').fill_null(0)      * 1    +
            _dataproc_term(col)
        )
        for col in all_scored
    }).drop(source_cols_to_drop)

    # 6. Apply direct lookups (structured fields from experiment TSV)
    df = _apply_structured_lookups(df)

    # 7. Resolve all labels
    df = _resolve_technology(df, tech_cols)
    df = _resolve_sc_or_bulk(df, tech_cols)
    df = _resolve_read_bias(df)
    df = _resolve_selection(df)
    df = _resolve_prep_kit(df, kit_cols)
    df = _resolve_tech_class(df)

    # 8. Flag cross-signal disagreements for downstream QC
    df = _flag_conflicts(df)

    df.write_csv('annotated_metadata_combined.csv')
    print('[wrote] annotated_metadata_combined.csv', file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            'Usage:\n'
            '  python metadata-annotate.py combine <run.tsv> <sample.tsv> <exp.tsv> <study.tsv> [<dataproc.tsv>]\n'
            '  python metadata-annotate.py fromcombined <all_zf_datescurated_withGEO.tsv>\n'
            '  python metadata-annotate.py buildonly <all_zf_datescurated_withGEO.tsv>',
            file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == 'combine':
        if len(sys.argv) not in (6, 7):
            print('combine requires 4 or 5 input files: <run> <sample> <exp> <study> [<dataproc>]',
                  file=sys.stderr)
            sys.exit(1)
        dataproc_f = sys.argv[6] if len(sys.argv) == 7 else None
        combine(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], dataproc_f)

    elif sys.argv[1] == 'fromcombined':
        if len(sys.argv) != 3:
            print('fromcombined requires exactly 1 input file', file=sys.stderr)
            sys.exit(1)
        run_f, sample_f, exp_f, study_f, dataproc_f = build_ugreppable_files(sys.argv[2])
        combine(run_f, sample_f, exp_f, study_f, dataproc_f)

    elif sys.argv[1] == 'buildonly':
        if len(sys.argv) != 3:
            print('buildonly requires exactly 1 input file', file=sys.stderr)
            sys.exit(1)
        build_ugreppable_files(sys.argv[2])

    else:
        # Single-file annotation (for testing / incremental use)
        for f in sys.argv[1:]:
            _annotate_file(f, keep_cols=['accession'])
