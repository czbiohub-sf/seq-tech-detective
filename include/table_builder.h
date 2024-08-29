#pragma once
#include <stdint.h>
#include <stdio.h>

#include "fingerprint_info.h"

typedef struct fp_hits {
	const char *name; // printable name
	enum sd_read_dir dir;  // forward/reverse read, as transformed
	enum sd_seq_type type; // tagged union for sequence
	int   id; // id, index in fingerprint table
	
	sd_fp_ofs_node *ofs; // list of expected offsets
	sd_range len; // length range, usually min == max except for certain barcode formats
	union {
		const uint32_t *bc_set; // SD_ONLIST: bitset ptr
		uint64_t seq_int; // SD_FIXED: sequence as uint
	};
	size_t hits[150]; // hit counts by position
} sd_fp_hits;

char *repr_fp_hit(sd_fp_hits *fph);
void dbg_log_fp_hit(sd_fp_hits *fph); // direct log_trace repr_fp_hit without mem mgmt req
char *fp_hits_tostr(sd_fp_hits *fph);
void print_fp_hits(sd_fp_hits *fph); // direct print fp_hits_tostr without mem mgmt req

// A = 00 ; C = 01 ; T = 10 ; G = 11
__attribute__((pure)) uint64_t seq_to_int(const char *seq_p, int len, int rc);

__attribute__((pure)) uint16_t seq_to_int16(const char seq_p[8]);
__attribute__((pure)) uint16_t seq_to_int16_rc(const char seq_p[8]);
__attribute__((pure)) uint32_t seq_to_int32(const char seq_p[16]);
__attribute__((pure)) uint32_t seq_to_int32_rc(const char seq_p[16]);
__attribute__((pure)) uint64_t seq_to_int64(const char seq_p[32]);
__attribute__((pure)) uint64_t seq_to_int64_rc(const char seq_p[32]);

char *int64_to_seq(uint64_t s);

void set_bit(uint32_t *table, const uint32_t key);
int  get_bit(const uint32_t *table, const uint32_t key);
// build bitset lookup tables for a given a barcode list
// caller is responsible for freeing memory when no longer needed
uint32_t *build_set(FILE *barcode_file, uint32_t width, enum sd_read_dir dir);

// testing fn
const uint32_t *build_10x_v2_bc_set(void);

sd_fp_hits **load_fingerprints(void);

void delete_fingerprints(sd_fp_hits **fp_hits);
