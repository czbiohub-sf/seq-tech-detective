#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "table_builder.h"

// result structure
struct res {
	size_t       len_reads;
	size_t       num_reads;
	size_t       polyt_hits;
	sd_fp_hits **fp_hits;
};


// serial reading
struct res fq_read(int fd, sd_fp_hits **fp_hits);
struct res fq_fread(FILE *fp, sd_fp_hits **fp_hits);
// parallel reading
struct res read_mt(int fd, off_t cur, off_t len, sd_fp_hits **fp_hits);
