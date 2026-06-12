# Seq-Detective (Core Mode)

![Seq-Detective "Magnifying Glass" Logo](docs/seq-detective-logo-c.svg "Seq-Detective Logo")

`seq-detective` classifies each FASTQ file in an RNA-seq accession as either biological (B) or
technical (T) by mapping a read sample to a host reference genome and applying a rule-based
decision tree to the resulting alignment metrics.  This is useful when processing public sequencing
archives at scale, where submitter-provided metadata is unreliable and library format cannot be
assumed.

The motivating problem: naive mass processing of SRA transcriptomic datasets routinely encounters
paired-end submissions where one mate contains barcodes, linkers, or other non-transcriptomic
sequence (e.g. 10x Chromium, inDrops, DeTCT).  These produce near-zero alignment rates in the
technical mate and silently distort downstream analyses.  A read-length heuristic is insufficient
because many single-cell submissions sequence both mates at identical lengths (2×75 bp, 2×150 bp).
Seq-Detective's mapping-based approach handles these cases without reference to submitter metadata.

This repository presents **Core Mode**: the mapping and B/T judgement pipeline used in the
RNAquarium study.  Full technology classification (specific chemistry identification) is not
available in this release.

## Installation

### Prerequisites

- [meson](https://mesonbuild.com/Getting-meson.html) ≥ 1.5
- OpenMP
- conda or mamba (for runtime dependencies)

Build the C components:

```sh
git clone https://github.com/czbiohub-sf/seq-tech-detective --depth=1
cd seq-tech-detective
meson setup build
meson compile -C build
```

Install runtime dependencies via conda:

```sh
conda env create -f environment.yml
conda activate seq-detective
```

Runtime dependencies include: `hisat2`, `featureCounts` (subread), `fastp`, `samtools`, `jq`, `bc`,
and `polars` (Python ≥ 3.10).

### Reference index

Download a reference genome assembly and build a HISAT2 index:

```sh
seq-detective index <assembly-name>
```

This downloads the assembly from NCBI, builds a HISAT2 index, and caches the paths under
`~/.local/state/seq-detective/`.  The thresholds in the judge were tuned against *Danio rerio*
GRCz12tu (NCBI RefSeq GCF_049306965.1); performance on other species or assemblies has not been
evaluated.

## Usage

### Core Mode: classify mates in an accession

```sh
seq-detective core <accession-prefix> <hisat2-index> <gtf> [outfile] [threads(8)]
```

FASTQ files matching `<accession-prefix>*.f*q` are each aligned independently in single-end mode.
Per-file metrics are written as a JSON object to `outfile` (default: stdout).

Pass the JSON output to the judge to get B/T labels:

```sh
seq-detective core SRR123456 /path/to/index /path/to/annotation.gtf | \
    seq-detective judge -b
```

Output (one line per file):

```
accession    filename    judgement    reason
SRR123456    SRR123456_1.fastq    T    sc-like readlen
SRR123456    SRR123456_2.fastq    B    sc-like readlen
```

#### Judge options

```
seq-detective judge -b [--per-acc] [-H] [--amend-paired-t] <file.json>

  -b                  core (B/T) mode — required
  --per-acc           one output line per accession instead of per file
  -H                  suppress header
  --amend-paired-t    if both mates are judged T but show sparse gene hits,
                      force the higher-mapping mate to B
```

### Map a single file

```sh
seq-detective core-map <file.fastq> <hisat2-index> <gtf> [outfile] [threads]
```

### Index management

```sh
seq-detective index <assembly-name>         # download + build index
seq-detective index <assembly-name> <nick>  # register under a short name
```

## How It Works

Each FASTQ file is processed independently:

1. **fastp** (Q17, minimum length 2 bp, polyX trimming) runs first to warm the OS file cache and
   collect pre-alignment QC statistics.
2. **HISAT2** aligns up to the sampled reads in single-end mode (`-k 1`,
   `--no-temp-splicesite`) against the host index.
3. **featureCounts** quantifies aligned reads against the host annotation, yielding mapping rate,
   no-feature rate, low-quality-mapping rate, gene count sparsity, and positive-strand ratio.
4. Metrics are serialized to JSON and consumed by **`judge.py -b`**, which applies a two-stage
   decision tree:

   - **Stage 1 — read length:** reads >500 bp → T (outside short-read aligner range).  For paired
     submissions, a mate with reads ≤29 bp paired with a mate ≥49 bp → T/B immediately (barcode
     length signature).
   - **Stage 2 — mapping metrics:** both mates <9% mapping rate → T/T (rejected as
     non-transcriptomic).  Otherwise, a signed percent-difference in mapping rate between mates
     (`mapping_diff = (r1 − r2) / max(r1, r2)`) is compared against a no-feature rate threshold
     (`nofeature_rate > ±0.6 × mapping_diff + 0.45`) to identify the technical mate.  Pairs that
     pass this envelope but have low minimum no-feature rate are accepted as B/B by biological
     fallback.  Single-end files use a simpler threshold: mapping rate ≥1.2% → B, below → T.

   Thresholds were fit by decision tree against ~60,000 human-curated expected decisions for *Danio
   rerio* GRCz12tu.

Runs where all files are classified T are non-transcriptomic or low-quality and can be excluded
from further processing.  For mixed B/T accessions, only the B-labeled files need to be carried
forward.

## Limitations

Core Mode assigns each file a binary B or T label.  Partially-technical library layouts — where
biological and technical sequence are interleaved within a single read (DeTCT being the clearest
example) — cannot be correctly handled by this classification.  The correct treatment for these
layouts is read-level trimming to recover the biological portion, which Core Mode does not perform
or recommend.  Partially-technical files that receive a B label will pass through as-is and may
show strand bias, reduced mapping rates, or quantification artifacts downstream.  Core Mode is
therefore best understood as a pre-filter that eliminates clearly technical mates from mixed
accessions; it does not solve the partially-technical case.

We are aware of this limitation and have observations on possible approaches.  If you encounter
these layouts at scale or are working toward a solution, we welcome contact and collaboration.

## Validation

Seq-Detective was validated against a manually curated benchmark of 150 accessions spanning bulk
RNA-seq, 10x Chromium, Smart-seq, CEL-seq, inDrops, and nine additional minority protocols,
selected for diversity in submission format (single FASTQ, paired FASTQ, BAM, CRAM, and mixed
archives).  Overall exact agreement with curated labels was 95.3%, with perfect agreement on 10x
(n=40) and 95.7% agreement on bulk (n=47).  Remaining disagreements were concentrated in unusual
submission formats (Smart-seq archived as interleaved BAM+CRAM) and DeTCT, whose reads partially
interleave biological and barcode sequence within a single file in a way that resists binary B/T
classification.

## Authors and maintainers

RNAquarium is developed and maintained by the [Computational Biology Platform](https://biohub.org/comp-biology/) & [Balla Group](https://biohub.org/balla/) at the [Biohub](https://biohub.org).

* **Research Lead Team:** Keir Balla, Duo Peng
* * **Bioinformatics Team:** Yttria Aniseia, Eric Waltari

## License

seq-detective is free and open source software distributed under the BSD 3-clause license except as
otherwise declared — see [LICENSE](LICENSE) for details.

All external code committed to the repository must be written under a compatible license that
permits inclusion in the `seq-tech-detective` source repository.

### Third-Party Notices

seq-detective includes a modified version of [log.c](https://github.com/rxi/log.c) by rxi under
the MIT license.

seq-detective uses [Tracy](https://github.com/wolfpld/tracy) by Bartosz Taudul under the BSD
3-clause license.

See the respective license files for details.
