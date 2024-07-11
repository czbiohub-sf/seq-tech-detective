#pragma once
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "library_layout_info.h"

enum BARCODE_LIST
{
	BC_10x_737_cratac_v1,
	BC_10x_737K_arc_v1,
	BC_10x_737K_april_2014_rc,
	BC_10x_737K_august_2016,
	BC_10x_3M_february_2018,
	BC_10x_9K_LT_march_2021,
};
enum CHEMISTRY
{
	CH_10X_RNA_V1,
	CH_10X_RNA_V2,
	CH_10X_RNA_V3,
	CH_10X_RNA_5,
	CH_10X_ATAC_V1,
	CH_10X_CRATAC,
	CH_10X_LT,
};

// is this table useless? we can only call the reverse
const enum BARCODE_LIST chem2bc[] =
{
	[CH_10X_RNA_V1] = BC_10x_737K_april_2014_rc,
	[CH_10X_RNA_V2] = BC_10x_737K_august_2016,
	[CH_10X_RNA_V3] = BC_10x_3M_february_2018,
	[CH_10X_RNA_5] = BC_10x_737K_august_2016,
	[CH_10X_ATAC_V1] = BC_10x_737K_arc_v1,
	[CH_10X_CRATAC] = BC_10x_737_cratac_v1,
	[CH_10X_LT] = BC_10x_9K_LT_march_2021
};

const char *BARCODE_MAP[] =
{
	[BC_10x_737K_august_2016] = "resources/cell-barcodes.10x.737K-august-2016.txt"
};


// A = 00 ; C = 01 ; T = 10 ; G = 11
// this compiles to SIMD shuffles when available
uint16_t seq_to_int16(const char seq_p[8]) __attribute__ ((const));
uint32_t seq_to_int32(const char seq_p[16]) __attribute__ ((const));
uint16_t seq_to_int16(const char seq_p[8])
{
	uint16_t result = 0;
	for (uint16_t i = 0; i < 8; i++) {
		result |= (uint16_t)((seq_p[i]) & 0b110) >> 1 << ((7-i)*2);
	}
	return result;
}

uint32_t seq_to_int32(const char seq_p[16])
{
	uint32_t result = 0;
	for (uint32_t i = 0; i < 16; i++) {
		result |= (uint32_t)((seq_p[i]) & 0b110) >> 1 << ((15-i)*2);
	}
	return result;
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

const size_t KBITS = 5, KMASK = 0x1F;
inline void set_bit(uint32_t *table, const uint32_t key)
{
	table[key >> KBITS] |= (1 << (key & KMASK));
}

inline int get_bit(const uint32_t *table, const uint32_t key)
{
	return (table[key >> KBITS] >> (key & KMASK)) & 1;
}
// build bitset lookup tables for a given a barcode list
// caller is responsible for freeing memory when no longer needed
uint32_t *build_set(FILE *barcode_file, uint32_t width)
{
	const size_t MAX_ENTRIES = (1UL << width) - 1;
	const size_t SIZEB = (MAX_ENTRIES >> KBITS) * sizeof(uint32_t);
	uint32_t *table = aligned_alloc(128, SIZEB);
	size_t buf_len = (width / 2) + 2; // need space for newbuf + nul
	char *buf = aligned_alloc(128, buf_len);
	ssize_t nread;
	if (width <= 16) {
		while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
			memset(&buf[nread-1], 0, buf_len - (nread-1)); //NOLINT
			set_bit(table, seq_to_int16(buf));
		}
	} else {
		while ((nread = getline(&buf, &buf_len, barcode_file)) >= 6) {
			memset(&buf[nread-1], 0, buf_len - (nread-1)); //NOLINT
			set_bit(table, seq_to_int32(buf));
		}
	}
	// TODO: check and report nread == -1, nread == 0, and small positive nread
	return table;
}

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
