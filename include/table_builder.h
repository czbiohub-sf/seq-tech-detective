#pragma once
#include <stdint.h>
#include <stdio.h>

enum BARCODE_LIST {
	BC_10x_737_cratac_v1,
	BC_10x_737K_arc_v1,
	BC_10x_737K_april_2014_rc,
	BC_10x_737K_august_2016,
	BC_10x_3M_february_2018,
	BC_10x_9K_LT_march_2021,
};
enum CHEMISTRY {
	CH_10X_RNA_V1,
	CH_10X_RNA_V2,
	CH_10X_RNA_V3,
	CH_10X_RNA_5,
	CH_10X_ATAC_V1,
	CH_10X_CRATAC,
	CH_10X_LT,
};

// A = 00 ; C = 01 ; T = 10 ; G = 11
__attribute__((pure)) uint16_t seq_to_int16(const char seq_p[8]);
__attribute__((pure)) uint32_t seq_to_int32(const char seq_p[16]);

void set_bit(uint32_t *table, const uint32_t key);
int  get_bit(const uint32_t *table, const uint32_t key);
// build bitset lookup tables for a given a barcode list
// caller is responsible for freeing memory when no longer needed
uint32_t *build_set(FILE *barcode_file, uint32_t width);

// testing fn
const uint32_t *build_10x_v2_bc_set(void);
