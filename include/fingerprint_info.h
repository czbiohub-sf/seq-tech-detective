#pragma once
#include <stdio.h>
#include <unistd.h>

// expected read file - but we mostly ignore this
enum sd_read_type
{
	SD_NONE = 0, SD_R1, SD_R2, SD_I1, SD_I2
};

enum sd_read_dir
{
	SD_DIR_UNK, SD_FWD, SD_REV
};

enum sd_seq_type
{
	SD_RANDOM, SD_FIXED, SD_ONLIST
};

// R1, ofs.min, ofs.max, seq.min, seq.max, type, sequence
typedef struct fingerprint {
	struct {
		off_t min;
		off_t max;
	} ofs;
	struct {
		size_t min;
		size_t max;
	} len;
	enum sd_read_type read; // "expected" readfile, usually ignored
	enum sd_read_dir  type; // forward/reverse read implies transform
	enum sd_seq_type  dir;  // tagged non-union for sequence
	char      *sequence;
} sd_fingerprint;

struct sd_library_fingerprint {
	char  *name;
	sd_fingerprint entries[6];
};
