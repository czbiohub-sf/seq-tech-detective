#include "fastq.h"

#include <errno.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <string.h>
#include <unistd.h>

#include "filereader.h"
#include "table_builder.h" // seq_to_int16, 32
#include "tracy.h"

// need to read next block into buffer for boundary-crossing reads
static const size_t BLKSIZE = (sizeof(char) * 4096 * 32);
static const size_t BUFSIZE = (BLKSIZE * 2); // * 2?
static const size_t ALIGN   = 128;

typedef enum {
	START_SKIP, // unknown state after seek
	ID_START,   // \n -> @
	ID,         // .* -> \n
	SEQ,        // [ACTGN]+ -> \n (normal)
	ID2_START,  // \n -> +
	ID2,        // .* -> \n
	QUAL,       // .* -> \n (same length as seq)

	ILLEGAL
} fastq_state;

static void add_res(struct res *out, struct res const *in)
{
	TracyCZoneS(ctx, 10, 1);
	out->len_reads  = out->len_reads + in->len_reads;
	out->num_reads  = out->num_reads + in->num_reads;
	out->polyt_hits = out->polyt_hits + in->polyt_hits;
	out->bc_hits    = out->bc_hits + in->bc_hits;
	TracyCZoneEnd(ctx);
}
#pragma omp declare reduction(+ : struct res : add_res(&omp_out, &omp_in)) \
	initializer(omp_priv = {0, 0, 0, 0})

// run through registered location + sequence checks and update
// TODO: this is just a proof of concept version of checks for now
void run_checks(size_t seq_len, const char seq[150], struct res *result, const uint32_t *bc_table)
{
	// for now, just checking 10x barcode list
	// eventually use the information in library_layout_info.h
	if (seq_len >= 16) {
		const uint32_t key = seq_to_int32(seq);
		if (get_bit(bc_table, key))
			result->bc_hits++;

		if (seq_len >= 16 + 10 + 8) {
			// TODO: this isn't good enough for poly-T
			if (seq_to_int16(&seq[26]) == seq_to_int16("TTTTTTTT"))
				result->polyt_hits++;
		}
	}
}

// serial reading
struct res fq_read(int fd, const uint32_t *bc_10x_v2)
{
	TracyCZoneS(ctx, 10, 1);
	struct res result = {0, 0, 0, 0};

	// 4096 should be plenty enough for any short read, right ?
	size_t  buflen = 4096;
	ssize_t have   = 0; // bytes in buffer
	char   *buf    = aligned_alloc(ALIGN, 4096);
	if (!buf)
		abort_msg("malloc failed");

	char   seq[151];
	size_t seq_len  = 0;
	size_t qual_len = 0;

	fastq_state state = ID_START;

	size_t ofs = 0; // position in file
	FILE  *fp  = fdopen(fd, "r");
	// TODO: assuming canonical one-line-per-field FASTQ
	// declare this restriction, or remove it if proven useful
	while ((have = getline(&buf, &buflen, fp)) > 0) {
		ofs += have;
		switch (state) {
		case START_SKIP: // skip until \n @
		case ID_START:   // read @ or fail
			if (buf[0] != '@')
				goto ILLEGAL;
			state = SEQ;
			break;
		case SEQ: // read [ACTGN] until \n
			// processing happens here
			seq_len = (size_t)have;
			// copy up to 150 bytes of sequence
			size_t seq_buf_len = seq_len < 150 ? seq_len : 150;
			memcpy(seq, &buf[0], seq_buf_len);
			// TODO: these may want to be buffered
			run_checks(seq_buf_len, seq, &result, bc_10x_v2);

			// increment total read length
			result.len_reads += seq_len;
			state = ID2_START;
			break;
		case ID2_START: // read + or fail
			if (buf[0] != '+')
				goto ILLEGAL;
			state = ID2;
			break;
		case ID2:  // skip until \n
			state = QUAL;
			break;
		case QUAL: // read exactly SEQ_LEN chars -> \n
			qual_len = have;
			if (qual_len != seq_len)
				goto ILLEGAL;
			result.num_reads++; // increment read count
			state = ID_START;
			break;
		ILLEGAL:
		case ILLEGAL:
		case ID:
		default:
			// illegal fastq_state ?
			fprintf(stderr, "fastq error around %zi\n", ofs);
			abort_msg("bad fastq"); // TODO: report error position
		}
	}

	if (result.num_reads > 0) {
		printf("reads: %zi\navg len: %zi\n10v2 hit rate: %f\n%f polyt hit rate\n",
		       result.num_reads,
		       result.len_reads / result.num_reads,
		       (double)result.bc_hits / (double)result.num_reads,
		       (double)result.polyt_hits / (double)result.num_reads);
	} else {
		printf("reads: 0\navg len: 0\n10v2 hit rate: 0\n0 polyt hit rate\n");
	}

	TracyCZoneEnd(ctx);
	return result;
}


// parallel reading
// based on https://github.com/expr-fi/fastlwc/blob/master/fastlwc-mt.c
struct res read_mt(int fd, off_t cur, off_t len, const uint32_t *bc_10x_v2)
{
	TracyCZoneS(ctx, 10, 1);
	// how many bufsize blocks
	const size_t blocks = ((size_t)len + BLKSIZE - 1) / BLKSIZE;

	struct res result = {0, 0, 0, 0};

#pragma omp parallel if (blocks > 1) reduction(+ : result)
	{
		int tidx = omp_get_thread_num();
		int tmax = omp_get_num_threads();
		TracyCSetThreadName("fastq_block_process");

		// reads can overlap block boundaries, so we need > BLKSIZE
		char *buf = aligned_alloc(ALIGN, BUFSIZE);

		if (!buf)
			abort_msg("malloc failed");

		// we need buffers to overlap into the next "block" area
		for (int i = 0, block; (size_t)(block = i * tmax + tidx) < blocks; ++i) {
			const off_t ofs = cur + (off_t)(BLKSIZE * (size_t)block); // file offset
			// bytes we want
			size_t bytes_left = BUFSIZE;
			// bytes in buffer
			size_t have = 0;
			char  *pos  = &buf[0];

			static const fastq_state block0_state[] = {START_SKIP, ID_START};
			fastq_state              state          = block0_state[block == 0];

			char    seq[151];
			size_t  seq_s           = 0;
			size_t  seq_len         = 0;
			ssize_t qual_s          = 0;
			ssize_t qual_len_remain = 0;

			// buffer file block -> process reads loop
			do {
				read_block_data(fd, buf, &have, &bytes_left, &ofs, block, (int)blocks);
				TracyCZoneS(ctx, 10, 1);

				char *cur_end = &buf[have];
				char  c;
				// check in bounds
#define EOD()          \
	if (pos > cur_end) \
	break
				// read char
#define READ() \
	EOD();     \
	(c = *(pos++))
				// peek char
#define PEEK() \
	EOD();     \
	(c = (*pos))
				// skip n
#define SKIP(n)                                              \
	pos = (cur_end) < (pos + (n)) ? (cur_end) : (pos + (n)); \
	EOD();
				// skip until
#define SCAN(d)                                     \
	while ((pos < cur_end) && ((*pos) != d)) ++pos; \
	EOD();                                          \
	++pos;

				// read from current parse step
				do {
					switch (state) {
					case START_SKIP: // skip until \n @
						SCAN('\n');
						PEEK();
						if (c == '@')
							state = ID_START;
						break;     // no fallthrough, keep scanning until we get to start state.
					case ID_START: // read @ or fail
						state = ID_START;
						READ();
						if (c != '@')
							goto ILLEGAL;
						[[fallthrough]];
					case ID: // skip until \n
						state = ID;
						SCAN('\n');

						seq_s = (size_t)(pos - buf);
						[[fallthrough]];
					case SEQ: // read [ACTGN] until \n
						state = SEQ;
						// processing happens here
						SCAN('\n');
						seq_len = (size_t)(pos - buf) - seq_s;
						// copy up to 150 bytes of sequence
						memcpy(seq, &buf[seq_s], seq_len < 150 ? seq_len : 150);
						// TODO: these may want to be buffered
						run_checks(seq_len, seq, &result, bc_10x_v2);

						// increment total read length
						result.len_reads += seq_len;
						seq_s = 0;
						[[fallthrough]];
					case ID2_START: // read + or fail
						state = ID2_START;
						READ();
						if (c != '+')
							goto ILLEGAL;
						[[fallthrough]];
					case ID2: // skip until \n
						state = ID2;
						SCAN('\n');
						qual_len_remain = -1;
						[[fallthrough]];
					case QUAL: // read exactly SEQ_LEN chars -> \n
						state = QUAL;
						// resume seq_len consume
						// TODO: we want a better framework for this kind of resume
						if (qual_len_remain == -1)
							qual_len_remain = (ssize_t)seq_len;
						else
							qual_len_remain -= ((pos - buf) - qual_s);
						qual_s = (pos - buf);
						SKIP(qual_len_remain);

						result.num_reads++; // increment read count
						state = ID_START;
						break;
					case ILLEGAL:
					default:;
					ILLEGAL:
						// illegal fastq_state ?
						abort_msg("bad fastq"); // TODO: report error position
					}

					// after block ends, ok to finish a partial sequence, but do not start a new one
					if ((state == ID_START) && (pos > (buf + BLKSIZE)))
						break;
					// otherwise we have more data and more entries to read
				} while (pos < cur_end);

				// stop reading if we aren't in the middle of a read
				// and we've crossed a block boundary
				// otherwise, go back to the top, read more, and keep parsing
				TracyCZoneEnd(ctx)
			} while (have < BLKSIZE && bytes_left);
		} // end block for
	}     // end parallel

	printf("reads: %zi\navg len: %zi\n10v2 hit rate: %f\n%f polyt hit rate\n",
	       result.num_reads,
	       result.len_reads / result.num_reads,
	       (double)result.bc_hits / (double)result.num_reads,
	       (double)result.polyt_hits / (double)result.num_reads);

	TracyCZoneEnd(ctx);
	return result;
}

// parse step state:
// DFA STATE
// buffer position
// end of available data
//
// local only:
// last read character
// - anything that could return a char must run out of memory WHEN relative to returning a char?
// case 1:
//
