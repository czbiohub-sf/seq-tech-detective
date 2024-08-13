#pragma once
#include <stdnoreturn.h>
#include <sys/types.h>

noreturn void abort_msg(const char *message);

// get more data, since only the parser knows if it doesn't have enough
// for seekable files (pread(2))
int read_block_data(
	int fd, char *buf, size_t *have, size_t *bytes_left, const off_t *ofs, int block, int blocks);
