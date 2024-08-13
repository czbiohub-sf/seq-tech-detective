#pragma once
#include <stdint.h>
#include <sys/types.h>

// result structure
struct res {
	size_t len_reads;
	size_t num_reads;
	size_t polyt_hits;
	size_t bc_hits; // we need all barcodes, and where are those specified?
};

// serial reading
struct res fq_read(int fd, const uint32_t *bc_10x_v2);
// parallel reading
struct res read_mt(int fd, off_t cur, off_t len, const uint32_t *bc_10x_v2);
