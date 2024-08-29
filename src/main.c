#include <config.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#include "log.h"
#include "fastq.h"
#include "filereader.h"
#include "table_builder.h"
#include "tracy.h"


noreturn static void usage()
{
	// TODO
	fprintf(stderr, "usage:\n");
	exit(EXIT_FAILURE);
}

int main(int argc, char **argv)
{
	TracyCZoneS(ctx, 10, 1);

	clock_t tstart = clock();
	sd_fp_hits **fp_hits = load_fingerprints();
	clock_t tloadedfp = clock();
	
	log_info("finished loading fingerprints in %.3f ms", 1000.0 * (tloadedfp - tstart) / CLOCKS_PER_SEC);
	
	// TODO: do we need to set _FILE_OFFSET_BITS ?
	if (argc < 1)
		usage();

	int fd = open(argv[1], O_RDONLY);
	if (fd < 0) {
		fprintf(stderr, "'%s': %s\n", argv[1], strerror(errno));
		abort_msg("could not open file");
	}

	off_t cur;
	off_t end;
	// TODO: this can fail, which would fall back to serial
	cur = lseek(fd, 0, SEEK_CUR);
	end = lseek(fd, 0, SEEK_END);

	posix_fadvise(fd, cur, end, POSIX_FADV_SEQUENTIAL | POSIX_FADV_WILLNEED);
	read_mt(fd, cur, end, fp_hits);

	delete_fingerprints(fp_hits);

	if (fd != STDIN_FILENO)
		close(fd);

	TracyCZoneEnd(ctx);
	return 0;
}
