extra fingerprint libraries can be loaded at runtime.

## Converting from seqspec
valid seqspec `spec.yaml` can be converted to seq-detective's format using
`scripts/seqspec2detective.py`

notably, the seqspec definition must have `Read` objects describing the primers.
the reads must include regions with onlists or fixed sequences.
`Read` names are expected to start with one of R1, R2, I1, I2.

`seqspec2detective.py <seqspec.yaml> -o outfile [-i|--header] [-f|--footer]`

the output is "fingerprint" info in c struct syntax usable by seq-detective.

passing -i/--header and -f/--footer adds includes and closes the struct array,
useful for scripting.  see `scripts/safe-exec.sh`