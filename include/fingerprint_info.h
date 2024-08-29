#pragma once
#include <stdint.h>
#include <sys/types.h>

// expected read file - but we mostly ignore this
enum sd_read_type { SD_NONE = 0, SD_R1, SD_R2, SD_I1, SD_I2 };

enum sd_read_dir { SD_DIR_UNK, SD_FWD, SD_REV };

enum sd_seq_type { SD_RANDOM, SD_FIXED, SD_ONLIST };

typedef struct fp_range {
	off_t min; // minimum, inclusive
	off_t max; // maximum, inclusive
} sd_range;

typedef struct ofs_node sd_fp_ofs_node;
typedef struct ofs_node {
	sd_fp_ofs_node *next;
	sd_range ofs;
} sd_fp_ofs_node;

// definitions format: sd_fingerprint
// R1, dir, type, ofs.min, ofs.max, len.min, len.max, sequence
typedef struct fingerprint {
	enum sd_read_type read; // "expected" readfile, usually ignored
	enum sd_read_dir  dir;  // forward/reverse read implies transform
	enum sd_seq_type  type; // tagged non-union for sequence

	sd_range ofs; // expected offset
	sd_range len; // length range, usually min == max except for certain barcode formats
	union {
		const char     *sequence; // for SD_FIXED: the seq bases, for SD_ONLIST: the filename
	};
} sd_fingerprint;

struct sd_library_fingerprint {
	const char    *name;
	sd_fingerprint entries[6];
};

extern const int NUM_FINGERPRINTS;

extern struct sd_library_fingerprint *fingerprints;
