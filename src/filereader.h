#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <omp.h>
#include <stdnoreturn.h>
#include <errno.h>

#include "tracy.h"

noreturn void abort_msg(const char *message)
{
	perror(message);
	exit(EXIT_FAILURE);
}

// get more data, since only the parser knows if it doesn't have enough
// for seekable files (pread(2))
int read_block_data(int fd, char *buf, size_t *have, size_t *bytes_left, const off_t *ofs,
					int block, int blocks)
{
	TracyCZoneS(ctx, 10, 1);
	// again: are overlapping preads a perf hit?
	ssize_t ilen = pread(fd, buf + *have, *bytes_left, *ofs + (off_t)*have);
	if (ilen > 0) {
		*bytes_left -= (size_t)ilen; // requests can be partially fulfilled
		*have += (size_t)ilen;
	} else if (ilen == 0) {
		if (block != (blocks - 1))
			abort_msg("unexpected end of file");
		// or, this is the last block
		*have = (size_t)ilen;
		*bytes_left = 0;
	} else {
		if (errno == EINTR) // oh worm?
			return EINTR; // will need to attempt read again
		abort_msg("read");
	}

	TracyCZoneEnd(ctx)
	return 0;
}
