import argparse
import io
import gzip
from pathlib import Path
from seqspec.Assay import Assay
from seqspec.Region import Onlist
import yaml

class RegionFingerprint:
    def __init__(self,
                 region: object,
                 read_id: str,
                 read_strand: str,
                 sequence_type: str,
                 sequence: str,
                 ofs_range: tuple[int, int],
                 len_range: tuple[int, int]
                 ) -> None:
        self.region = region
        self.read_id = read_id
        self.read_strand = read_strand
        self.sequence_type = sequence_type
        self.sequence = sequence
        self.ofs_range = ofs_range
        self.len_range = len_range

# roughly follow the same pattern as seqspec index
# in case we want to be incorporated into it at some point
def load_spec(spec: str):
    with Path(spec).open("r") as f:
        data = yaml.load(f, yaml.Loader)
        return data


def setup_args(parser):
    parser.add_argument("yaml", help="Sequencing specification yaml file")
    parser.add_argument(
        "-o",
        metavar="OUT",
        help=("Path to output file"),
        type=str,
        default=None,
    )

    return parser


def validate_index_args(parser, args):
    file = args.yaml
    out = args.o

    spec = load_spec(file)
    x = run(spec)
    if out:
        with Path(out).open("w") as f:
            print(x, file=f)
    else:
        print(x)
    return


def run(spec):
    indices = []
    for read in spec.sequence_spec:
        index = get_index(spec, read.read_id)
        indices.append(index)
    return format_seq_detective(spec, indices)


# seqspec utils.py
def map_read_id_to_regions(spec, read_id):
    leaves = spec.get_libspec('rna').get_leaves()
    read = [i for i in spec.sequence_spec if i.read_id == read_id][0]
    primer_id = read.primer_id
    primer_idx = [i for i, l in enumerate(leaves) if l.region_id == primer_id][0]

    # iteration direction
    if read.strand == "neg":
        rgns = leaves[:primer_idx][::-1]
    else:
        rgns = leaves[primer_idx + 1:]
    return (read, rgns)


def get_index(spec, read_id) -> dict[str, list[tuple[object, str, str, tuple[int, int], tuple[int, int]]]]:
    (read, rgns) = map_read_id_to_regions(spec, read_id)

    vecs = []
    ofs_min = 0
    ofs_max = 0
    for region in rgns:
        ofs = (ofs_min, ofs_max)
        length = (region.min_len, region.max_len)
        sequence = region.onlist.filename if region.sequence_type=="onlist" else region.sequence
        vecs.append(RegionFingerprint(region, read_id, read.strand, region.sequence_type, sequence, ofs, length))
        ofs_min = ofs_min + region.min_len
        ofs_max = ofs_max + region.max_len
        # until sequencing read length met
        if (ofs_max) >= read.max_len:
            break

    return {read_id: vecs}
    

def format_seq_detective(spec, indices: list[dict[str, list[RegionFingerprint]]]):
    s = f"""\t{{\n\t\t\"{spec.name}\", {{\n"""
    for idx, read in enumerate(indices):
        for read, regions in read.items():
            for region in regions:
                if region.sequence_type in ["fixed", "onlist"]:
                    seq_type = {"fixed": "SEQ_FIXED", "onlist": "SEQ_ONLIST", "random": "SEQ_RANDOM"}[region.sequence_type]
                    seq_dir = {"pos": "SEQ_FWD", "neg": "SEQ_REV"}[region.read_strand]
                    exp_read = region.read_id[0:2]
                    ofs_range = f"{{{region.ofs_range[0]:>2}, {region.ofs_range[1]:>2}}}"
                    len_range = f"{{{region.len_range[0]:>2}, {region.len_range[1]:>2}}}"
                    s += f"\t\t\t{{ {ofs_range}, {len_range}, {exp_read}, {seq_type:>10}, {seq_dir}, \"{region.sequence}\"}},\n"

    s += """\t\t\t{ 0 }\n\t}"""
    return s

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    setup_args(parser)
    args = parser.parse_args()
    validate_index_args(parser, args)