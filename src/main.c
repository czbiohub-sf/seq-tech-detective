#include <errno.h>
#include <fcntl.h>
#include <stdnoreturn.h>
#include <unistd.h>

#include "tracy.h"
#include "table_builder.h"
#include "filereader.h"
#include "fastq.h"


noreturn void usage()
{
	// TODO
	fprintf(stderr, "usage:\n");
	exit(EXIT_FAILURE);
}

// testing fn
const uint32_t *build_10x_v2_bc_set()
{
	const uint32_t bc_len = 16;
	FILE *f_bc_list = fopen(BARCODE_MAP[chem2bc[CH_10X_RNA_V2]], "r");
	posix_fadvise(fileno(f_bc_list), 0, 0, POSIX_FADV_SEQUENTIAL | POSIX_FADV_WILLNEED);
	const uint32_t *bc_set = build_set(f_bc_list, bc_len * 2);
	posix_fadvise(fileno(f_bc_list), 0, 0, POSIX_FADV_DONTNEED);

	return bc_set;
}

int main(int argc, char **argv)
{
	TracyCZoneS(ctx, 10, 1);

	// TODO: this goes in a big list of checks we want to run
	const uint32_t *bc_10x_v2 = build_10x_v2_bc_set();

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
	read_mt(fd, cur, end, bc_10x_v2);

	if (fd != STDIN_FILENO)
		close(fd);

	TracyCZoneEnd(ctx)
	return 0;
}
