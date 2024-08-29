#include "table_builder.h"

#include <fcntl.h>
#include <linux/limits.h>
#include <search.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tracy.h"
#include "config.h"
#include "fingerprint_info.h"
#include "log.h"


// TODO: tables shared between assays, but we also need to not run them multiple times.
// and possibly to count as hits for all.  i.e. maybe we need another level of indirection
// around onlist hits.
static sd_fp_hits **fingerprint_ids;

// fingerprint hit-related library functions

// debug print sd_fp_hits fields
// caller must free returned pointer!
char *repr_fp_hit(sd_fp_hits *fph)
{
	const char fmt[] = "fp_hits { name: %s, dir: %c, type: %c, id: %d, "
		"ofs: %p {%zd, %zd}, len: {%zi, %zi}, seq: %s }";
	char *buf = NULL;
	char *seq = int64_to_seq(fph->seq_int);
	int sz = 0;
	for (int i = 0; i < 2; i++) {
		if (i != 0) buf = malloc(sz);
		sz = snprintf(buf, sz, fmt,
					  fph->name, "UFR"[fph->dir], "RFO"[fph->type], fph->id,
					  (void *)fph->ofs,
					  fph->ofs == NULL ? -1 : fph->ofs->ofs.min,
					  fph->ofs == NULL ? -1 : fph->ofs->ofs.max,
					  fph->len.min, fph->len.max,
					  fph->type == SD_FIXED ? seq : "(onlist)"
			) + 1;
	}
	free(seq);
	return buf;
}

void dbg_log_fp_hit(sd_fp_hits *fph)
{
	char *msg = repr_fp_hit(fph);
	log_trace("%s", msg);
	free(msg);
}

// get stringified hit counts by position in specified fingerprint counter
// caller must free returned pointer!
char *fp_hits_tostr(sd_fp_hits *fph)
{
	const int sz = 2048;
	char *msg = malloc(sz);
	int e;
	int maxpos = sizeof(fph->hits) / sizeof(size_t);
	// SEQUENCENAME: [pos: val, pos: val]
	e = snprintf(msg, sz, "%s: [", fph->name);
	for (int i = 0; i < maxpos; ++i) {
		if (fph->hits[i] > 0)
			e += snprintf(msg + e, sizeof(msg) - e, "%d: %zi, ", i, fph->hits[i]);
	}
	snprintf(msg + e, sizeof(msg) - e, "]");
	return msg;
}

void print_fp_hits(sd_fp_hits *fph)
{
	char *msg = fp_hits_tostr(fph);
	printf("%s\n", msg);
	free(msg);
}

// sd_fp_hits constructor
sd_fp_hits *init_fp_hit(const sd_fingerprint *rgn, int id, enum sd_read_dir dir)
{
	sd_fp_hits *fp_id = (sd_fp_hits *)malloc(sizeof(sd_fp_hits));
	*fp_id = (sd_fp_hits) {
        .name = rgn->sequence,
		.dir  = dir,
		.type = rgn->type,
		.id   = id,
		.len  = { .min = rgn->len.min, .max = rgn->len.max },
        .seq_int = 0L,
		.ofs     = (sd_fp_ofs_node *)malloc(sizeof(sd_fp_ofs_node)),
		.hits    = {0}
	};
	fp_id->ofs->next = NULL;
	fp_id->ofs->ofs.min = rgn->ofs.min;
	fp_id->ofs->ofs.max = rgn->ofs.max;

	return fp_id;
}

// add an offset to the list of expected offsets for a region
void update_expected_ofs(sd_fp_hits *fp_id, const sd_fingerprint *rgn)
{
	sd_range n_ofs = rgn->ofs;
	if (fp_id->ofs == NULL) {
		fp_id->ofs = (sd_fp_ofs_node *)malloc(sizeof(sd_fp_ofs_node));
		fp_id->ofs->ofs = (sd_range){ .min = n_ofs.min, .max = n_ofs.max };
		fp_id->ofs->next = NULL;
		return;
	}
	sd_fp_ofs_node *cur_ofs_node = fp_id->ofs;
	while (cur_ofs_node != NULL && cur_ofs_node->next != NULL) {
		sd_range cur_ofs = fp_id->ofs->ofs;
		// expand right
		if (cur_ofs.max >= n_ofs.min)
			cur_ofs.max = cur_ofs.max < n_ofs.max ? n_ofs.max : cur_ofs.max;
		// expand left
		if (cur_ofs.min <= n_ofs.max)
			cur_ofs.min = cur_ofs.min < n_ofs.min ? n_ofs.min : cur_ofs.min;
		
		if (cur_ofs.max >= n_ofs.min || cur_ofs.min <= n_ofs.max)
			return; // updated an entry, done here
		
		if (cur_ofs_node->next == NULL)
			break; // add a new offset node
		cur_ofs_node = cur_ofs_node->next; // keep searching
	}
	cur_ofs_node->next = (sd_fp_ofs_node *)malloc(sizeof(sd_fp_ofs_node));
	cur_ofs_node->next->ofs = (sd_range) { .min = n_ofs.min, .max = n_ofs.max };
	cur_ofs_node->next->next = NULL;
}



ENTRY *get_fingerprint_id(const sd_fingerprint *rgn)
{
	ENTRY ol_entry;
	ol_entry.key  = (char *)rgn->sequence;
	ol_entry.data = NULL;
	return hsearch(ol_entry, FIND);
}

void ll_delete(sd_fp_ofs_node *ofs)
{
	if (ofs->next)
		ll_delete(ofs->next);
	free(ofs->next);
}
void delete_fingerprints(sd_fp_hits **fp_hits)
{
	for ( ; *fp_hits != NULL; ++fp_hits) {
		sd_fp_hits *fp_hit = *fp_hits;
		if (fp_hit->type == SD_ONLIST)
			free(fp_hit->bc_set);
		ll_delete(fp_hit->ofs);
		free(fp_hit->ofs);
		free(fp_hit);
	}
}

// fingerprint_ids: [fp, fp_rc, fp2, fp2_rc]
 
// load all barcode tables
sd_fp_hits **load_fingerprints(void)
{
	TracyCZoneS(ctx, 10, 1);
	const size_t PATH_MX = 4096; // limits.h, sometimes
	char         path[PATH_MX];
	ENTRY        rgn_seq_entry, *found_rgn;

	hcreate(NUM_FINGERPRINTS * 4);
	
	int num_fpr = 0;
	// TODO: this can need realloc, build out real structure
	fingerprint_ids = calloc(NUM_FINGERPRINTS * 6 * 2, sizeof(sd_fp_hits *));
	for (int i = 0; i < NUM_FINGERPRINTS; ++i) {
		struct sd_library_fingerprint fgpts = fingerprints[i];
		for (sd_fingerprint *rgn = &fgpts.entries[0]; rgn->read != SD_NONE; ++rgn) {
			found_rgn = get_fingerprint_id(rgn);
			if (found_rgn != NULL) {
				log_info("cached: %s R%d region %s", fgpts.name, rgn->read, rgn->sequence);
				sd_fp_hits *fpr = (sd_fp_hits *)found_rgn->data;
				update_expected_ofs(fpr, rgn);
				update_expected_ofs(fingerprint_ids[fpr->id + 1], rgn); // update rc as well
				continue;
			}

			// not in cache, create a new fp_hits struct
			switch (rgn->type) {
			case SD_ONLIST:
				snprintf(path, PATH_MX, "%s/%s", PKGDATADIR, rgn->sequence);
				FILE *onlist_fp = fopen(path, "r");
				if (onlist_fp == NULL) {
					log_warn("not found: %s R%d ONLIST %s", fgpts.name, rgn->read, path);
					continue;
				}

				// onlist file is valid and new: build table and associate with fingerprint
				log_info("found: %s R%d ONLIST %s", fgpts.name, rgn->read, rgn->sequence);

				posix_fadvise(fileno(onlist_fp), 0, 0, POSIX_FADV_SEQUENTIAL | POSIX_FADV_WILLNEED);
				// store the pointer to the newly created table
				// TODO: build set should generate both fwd and reverse
				fingerprint_ids[num_fpr] = init_fp_hit(rgn, num_fpr, SD_FWD);
				fingerprint_ids[num_fpr]->bc_set = build_set(onlist_fp, rgn->len.max * 2, SD_FWD);
				dbg_log_fp_hit(fingerprint_ids[num_fpr]);
				++num_fpr;
				fingerprint_ids[num_fpr] = init_fp_hit(rgn, num_fpr, SD_REV);
				fingerprint_ids[num_fpr]->bc_set = build_set(onlist_fp, rgn->len.max * 2, SD_REV);
				dbg_log_fp_hit(fingerprint_ids[num_fpr]);
				++num_fpr;

				posix_fadvise(fileno(onlist_fp), 0, 0, POSIX_FADV_DONTNEED);
				fclose(onlist_fp);

				rgn_seq_entry.key = (char *)rgn->sequence;
				rgn_seq_entry.data = fingerprint_ids[num_fpr - 2];
				hsearch(rgn_seq_entry, ENTER);
				break;
			case SD_FIXED:
				log_info("found: %s R%d FIXED %s", fgpts.name, rgn->read, rgn->sequence);
				int seq_len = strlen(rgn->sequence);
				if (seq_len > 32)
					log_warn("FIXME! too long linker: %s (%s)", fgpts.name, rgn->sequence);

				fingerprint_ids[num_fpr] = init_fp_hit(rgn, num_fpr, SD_FWD);
				fingerprint_ids[num_fpr]->seq_int =
					seq_to_int(rgn->sequence, seq_len, false);
				dbg_log_fp_hit(fingerprint_ids[num_fpr]);
				++num_fpr;
				fingerprint_ids[num_fpr] = init_fp_hit(rgn, num_fpr, SD_REV);
				fingerprint_ids[num_fpr]->seq_int =
					seq_to_int(rgn->sequence, seq_len, true);
				dbg_log_fp_hit(fingerprint_ids[num_fpr]);
				++num_fpr;
				
				rgn_seq_entry.key = (char *)rgn->sequence;
				rgn_seq_entry.data = fingerprint_ids[num_fpr - 2];
				hsearch(rgn_seq_entry, ENTER);
				break;
			case SD_RANDOM:
				log_warn("RANDOM region on %s, R%d ignored", fgpts.name, rgn->read);
				break;
			default:
				log_warn("bad region '%d' on %s, R%d ignored", rgn->type, fgpts.name, rgn->read);
			}
		} // foreach region in fingerprint
	} // foreach assay fingerprint

	TracyCZoneEnd(ctx);
	return fingerprint_ids;
}


// A = 00 ; C = 01 ; T = 10 ; G = 11
// the 32-bit version compiles to SIMD shuffles when available
__attribute__((pure)) uint16_t seq_to_int16(const char seq_p[8])
{
	uint16_t result = 0;
	for (uint8_t i = 0; i < 8; i++) {
		char base = (seq_p[i] >> 1U) & 0b11;
		result |= (uint16_t)base << ((7 - i) * 2);
	}
	return result;
}

__attribute__((pure)) uint32_t seq_to_int32(const char seq_p[16])
{
	uint32_t result = 0;
	for (uint8_t i = 0; i < 16; i++) {
		char base = (seq_p[i] >> 1U) & 0b11;
		result |= (uint32_t)base << ((15 - i) * 2);
	}
	return result;
}

__attribute__((pure)) uint64_t seq_to_int64(const char seq_p[32])
{
	uint64_t result = 0;
	for (uint8_t i = 0; i < 32; i++) {
		char base = (seq_p[i] >> 1U) & 0b11;
		result |= (uint64_t)base << ((31 - i) * 2);
	}
	return result;
}

__attribute__((pure)) uint16_t seq_to_int16_rc(const char seq_p[8])
{
	uint16_t result = 0;
	for (uint8_t i = 0; i < 8; i++) {
		char base = ((seq_p[i] >> 1U) ^ 0b10) & 0b11;
		result |= (uint16_t)base << (i * 2);
	}
	return result;
}

__attribute__((pure)) uint32_t seq_to_int32_rc(const char seq_p[16])
{
	uint32_t result = 0;
	for (uint8_t i = 0; i < 16; i++) {
		char base = ((seq_p[i] >> 1U) ^ 0b10) & 0b11;
		result |= (uint32_t)base << (i * 2);
	}
	return result;
}

__attribute__((pure)) uint64_t seq_to_int64_rc(const char seq_p[32])
{
	uint64_t result = 0;
	for (uint8_t i = 0; i < 32; i++) {
		char base = ((seq_p[i] >> 1U) ^ 0b10) & 0b11;
		result |= (uint64_t)base << (i * 2);
	}
	return result;
}

// seq_to_int with correct length dispatch and masking
inline uint64_t seq_to_int(const char *seq_p, int len, int rc)
{
	if (!rc) {
		if (len <= 8)
			return seq_to_int16(seq_p)  & (~0UL << (16 - (len * 2)));
		else if (len <= 16)
			return seq_to_int32(seq_p)  & (~0UL << (32 - (len * 2)));
		else if (len <= 32)
			return seq_to_int64(seq_p)  & (~0UL << (64 - (len * 2)));
		// TODO: this is either bad stopgap
		// or an intentional behavior to be formalized.
		return seq_to_int64(seq_p)  & (~0UL << (64 - (len * 2)));
	} else {
		if (len <= 8)
			return seq_to_int16_rc(seq_p)  & ((1UL << (len * 2)) - 1);
		else if (len <= 16)
			return seq_to_int32_rc(seq_p)  & ((1UL << (len * 2)) - 1);
		else if (len <= 32)
			return seq_to_int64_rc(seq_p)  & ((1UL << (len * 2)) - 1);
		return seq_to_int64_rc(seq_p)  & ((1UL << (len * 2)) - 1);
	}
}

// convert bit-packed sequence <=32bp to string
char *int64_to_seq(uint64_t s)
{
	char *seq = malloc(33);
	for (int i = 31; i >= 0; i--) {
		seq[31 - i] = "ACTG"[(s & (3L << i * 2)) >> (i * 2)];
	}
	seq[32] = '\0';
	return seq;
}


// bitset tables
const size_t KBITS = 5, KMASK = 0x1F;
// bitset w/ uint32 bins setter/getter
inline void set_bit(uint32_t *table, const uint32_t key)
{
	table[key >> KBITS] |= (1UL << (key & KMASK));
}

inline int get_bit(const uint32_t *table, const uint32_t key)
{
	return (table[key >> KBITS] >> (key & KMASK)) & 1UL;
}

// build bitset lookup tables for a given a barcode list
uint32_t *build_set(FILE *barcode_file, uint32_t width, enum sd_read_dir dir)
{
	const size_t MAX_ENTRIES = (1UL << width) - 1;
	// entries / bits-per-cell * bytes-per-cell
	const size_t SIZEB       = (MAX_ENTRIES >> KBITS) * sizeof(uint32_t);
	//uint32_t    *table       = (uint32_t *)aligned_alloc(128, SIZEB);
	uint32_t    *table       = (uint32_t *)calloc(MAX_ENTRIES >> KBITS, sizeof(uint32_t));
	//width = 1 << (32 - __builtin_clzl(width - 1));
	size_t       buf_len     = (width / 2) + 2; // need space for newbuf + nul
	if (width < 16)
		buf_len = 8 + 2;
	else if (width < 32)
		buf_len = 16 + 2;
	else if (width < 64)
		buf_len = 32 + 2;
	char        *buf         = (char *)aligned_alloc(128, buf_len);
	ssize_t      nread;

	if (width <= 16) {
		if (dir != SD_REV) {
			while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
				memset(&buf[nread - 1], 0, buf_len - (nread - 1)); // NOLINT
				set_bit(table, (const uint32_t)seq_to_int16(buf));
			}
		} else {
			while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
				memset(&buf[nread - 1], 0, buf_len - (nread - 1)); // NOLINT
				set_bit(table, (const uint32_t)seq_to_int16_rc(buf));
			}
		}
	} else {
		if (dir != SD_REV) {
			while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
				memset(&buf[nread - 1], 0, buf_len - (nread - 1)); // NOLINT
				set_bit(table, seq_to_int32(buf));
			}
		} else {
			while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
				memset(&buf[nread - 1], 0, buf_len - (nread - 1)); // NOLINT
				set_bit(table, seq_to_int32_rc(buf));
			}
		}
	}

	free(buf);
	// TODO: check and report nread == -1, nread == 0, and small positive nread
	return table;
}

// cases:
// barcode is 16bp
//  - convert to u32
// barcode is 12bp
//  - convert to u32
//  - which side is empty?
// barcode is vl 8-11bp
//  - convert to u32 ?
//  - or   use only first 8bp?
// barcode is 8bp
//  - convert to u16


// tables:
//
// COMPLETELY RANDOM?, NOT HANDLED BY BC CHECK
//
// Drop-seq (20 bp : Drop-seq_Alignment_Cookbook.pdf)
//  error rate: >50% 0.25
//    ^cell barcode: 12 bases
//    + mol barcode: 8 bases often NNGGGGGG (??)
//   may be B20 B50 T8
// CEL-Seq https://github.com/kharchenkolab/dropEst/blob/master/configs/cel_seq2.xml
//    ^cell barcode: 8 bases
// CEL-Seq2 https://github.com/kharchenkolab/dropEst/blob/master/configs/cel_seq2.xml
//    ^cell barcode: 6 bases
//    + umi barcode: 4 bases
// Seq-well (also split-seq)
//   may be
//   ^cell barcode: 12 bases
//   ^ umi barcode: 8 bases
// SPLiT-seq
//
// iCLIP
//   barcodes at start of sequence
//   ^cell barcode: 2 bp
//   + umi barcode: 3 bp
//
// NON-RANDOM OR POSSIBLE CHARACTERISTICS
//
// 10x:
// 3M-february-2018.txt.gz => Single Cell 3' v3/v3.1/HT v3.1
// 737K-august-2016.txt.gz => Single Cell 5' v1/v2/HT v2/3' v2
// 737K-april-2014_rc.txt  => Single Cell 3' v1
// 737K-arc-v1.txt.gz      => Single Cell ATAC/ATAC+GEX v1
// 737-cratac-v1.txt.gz    => Single Cell ATAC
// 9K-LT-march-2021.txt.gz => Single Cell 3' LT
//
//   ^cell barcode: 16 bp
//   + umi barcode: 10 bp oft. NNNTTTTTTT (??)
// should be 16bp + 10bp for T8 B26 B
// (how different are these ?)
//
// 10x v1: R2: 10bp UMI  /  I1: 14bp 737K-april-2014_rc.txt.gz
// 10x v2: R1: 16bp 737K-august-2016.txt.gz + 10bp UMI
// 10x 5': R1: 16bp 737K-august-2016.txt.gz + 10bp UMI
// 10x v3: R1: 16bp 3M-february-2018.txt.gz + 12bp UMI
//
// inDrops (10.1038/nprot.2016.154)
//  error rate: >70% 0.25, >10% 0.5
//   have not seen an accession that includes the barcode data yet
//   AAGGCGTCACAAGCAATCACTC [BARCODE*] AGATCGGAAGAGCGTCGTGTAGGGAAAGAG
//   "two-step synthesis of a library of 147,456 unique barcode"
//     384, variable length, 8-11bp ?  multiple barcodes ?
//
// inDrops v1 & v2 https://github.com/kharchenkolab/dropEst/blob/master/configs/indrop_v1_2.xml
//   ^cell barcode 1 (8-11)
//   + spacer AAGGCGTCACAAGCAATCACTC (revcomp GAGTGATTGCTTGTGACGCCTT)
//   +cell barcode 2 (8)
//   + umi barcode 1 (6) often C/A C/A C/A C/T T/C T/C (CCCCTT) (AAATCC)
//   we could look for 8-11 bp in for GAGTGATTGCTTGTGACGCCTT (22bp) with up to 4 errors
//   v1 has barcode in r1, v2 has barcode in r2
//   "Barcode1 has variable lengths, but the first 8 bp are exactly the same as Barcode2"
//   "we should use the reverse complement of the barcode sequences for the whitelists"
// inDrop v3 https://github.com/kharchenkolab/dropEst/blob/master/docs/droptag.rst
//  R1: cDNA
//  I1:
//   ^cell barcode 1 (8 bp?)
//  I2/R2:
//   index
//  R2/R3:
//   ^cell barcode 2 (8 bp)
//   + umi barcode 2 (6 bp)
//  "Barcode1 has variable lengths, but the first 8 bp are exactly the same as Barcode2"
//  "Barcode1 is sequenced in the opposite direction of the bead oligo with only 8 cycles, so we
//   need to use the first 8 bp of Barcode1 as they are. Barcode2 is sequenced in the same
//   direction of the bead oligo, so we should take the reverse complement of the barcode sequence"
//
// Microwell-seq
//  3 barcodes with linkers
//   ^cell barcode 1 (6 bp) might have a 96-entry onlist?
//   + linker 1     (15 bp) CGACTCACTACAGGG
//   +cell barcode 2 (6 bp) in real world may be from same onlist as cbc1 ... is seqspec wrong?
//   + linker 2     (15 bp) TCGGTGACACGATCG
//   +cell barcode 3 (6 bp) in real world may be from same onlist as cbc1 ...
//   + umi barcode 1 (6 bp)
//
// sciRNAseq
//  52 bp cDNA
//  R1: (18 bp)
//   ^ umi barcode (8 bp)
//   +  rt barcode (10 bp) first plate well barcode
//  I1: 8 or 10 bp         second plate well barcode
//  I2: 8 or 10 bp         second plate well barcode
//
// sciRNAseq-3
// 50+ bp cDNA
// R1: (34 bp)
//   ^hairpin bc   (9 or 10 bp) second plate well barcode
//   + linker 1    (6 bp) CAGAGC
//   + umi barcode (8 bp)
//   +  rt barcode (10 bp)      first plate well barcode
// I1: 8 or 10 bp               third plate well barcode
// I2: 8 or 10 bp               third plate well barcode


// 10x:
// read must be >= 26bp
// check for hamming-1 barcode hits within first 3 bases
// 10x v1: R2: 10bp UMI  /  I1: 14bp 737K-april-2014_rc.txt.gz
// 10x v2: R1: 16bp 737K-august-2016.txt.gz + 10bp UMI
// 10x 5': R1: 16bp 737K-august-2016.txt.gz + 10bp UMI
// 10x v3: R1: 16bp 3M-february-2018.txt.gz + 12bp UMI

// inDrops v1 & v2 https://github.com/kharchenkolab/dropEst/blob/master/configs/indrop_v1_2.xml
// read must be >= 30bp
// if [0..8] is inDrops barcode 1 hit, then:
//   check for hamming-2 (ideal 4 but impractical?) spacer at positions 8-11
//   + spacer AAGGCGTCACAAGCAATCACT[C] (rev comp of GAGTGATTGCTTGTGACGCCTT)
//   if read >= 38 bp:
//     check for [0..8] == [30..38] | [31..39] | [32..40] ?  inconsistent whether this is in r1
// inDrop v3 https://github.com/kharchenkolab/dropEst/blob/master/docs/droptag.rst
// read must be >= 14
// if [0..8] is inDrops barcode 2 hit, then:
//   that's all.  corroborate with technical lengths later.
//   "Barcode2 is sequenced in the same direction of the bead oligo, so we
//    should take the reverse complement of the barcode sequence"
