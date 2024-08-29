#include "fingerprint_info.h"

// clang-format off
static struct sd_library_fingerprint fingerprints2[] = {
	// library name
	//		  read,  dir,     type,      ofs,      len,      sequence source
	{
		"10x-RNA-v2", {
			{ SD_R1, SD_FWD,  SD_ONLIST, { 0,  0}, {16, 16}, {"cb_10x_737K-august-2016.txt"} },
			//{ SD_R1, SD_FWD, SD_RANDOM, {16, 16}, { 8,  8} }, // umi
			{ SD_I1, SD_FWD,  SD_ONLIST, { 0,  0}, { 8,  8}, {"index7_onlist.txt"} },
			{ SD_NONE },
		}
	},
	{
		"inDropv2", {
			{ SD_I1, SD_FWD,  SD_ONLIST, { 0,  0}, { 6,  6}, {"sample_index_onlist.txt"} },
			{ SD_R2, SD_REV,  SD_ONLIST, { 0,  0}, { 8, 11}, {"cb_indrop_bc1.txt"} },
			{ SD_R2, SD_REV,   SD_FIXED, { 8, 11}, {22, 22}, {"AAGGCGTCACAAGCAATCACTC"} },
			{ SD_R2, SD_REV,  SD_ONLIST, {30, 33}, { 8,  8}, {"cb_indrop_bc2.txt"} },
			//{ SD_R2, SD_REV, SD_RANDOM, { 38, 41}, { 8,  8} }, // umi
			{ SD_NONE },
		}
	},
};
// clang-format on
const int NUM_FINGERPRINTS = sizeof(fingerprints2) / sizeof(struct sd_library_fingerprint);
struct sd_library_fingerprint *fingerprints = fingerprints2;

/*
 * { // Microwell-seq: 6bp BC1 + 15bp LN1 + 6bp BC2 + 15bp LN2 + 6bp BC3 + 6bp UMI
 * 	"Microwell-seq", {
 * 		//{ SD_R1, SD_FWD, SD_ONLIST, { 0,  0}, { 6,  6}, SEQ_ONLIST, NULL }, // plate 1 cell
 * barcode { SD_R1, SD_FWD, SEQ_FIXED, { 6,  6}, {15, 15}, "CGACTCACTACAGGG" }, // linker 1
 * 		//{ SD_R1, SD_FWD, SEQ_ONLIST, {21, 21}, { 6,  6}, NULL }, // plate 2 cell barcode
 * 		{ SD_R1, SD_FWD, SEQ_FIXED, {27, 27}, {15, 15}, "TCGGTGACACGATCG" }, // linker 2
 * 		//{ SD_R1, SD_FWD, SEQ_ONLIST, {42, 42}, { 6,  6},  NULL }, // plate 3 cell barcode
 * 		{ 0 }
 * 	}
 * },
 */
/*
 * {
 * 	"inDropsv3", { // TODO: SD_R1 and R4(SD_I2) ?
 * 		{ SD_R1, { 0,  0}, { 8, 11}, SEQ_ONLIST, "indrops_onlist2.txt" }, // cell barcode 2
 * 		//{ SD_I2, { 0,  0}, { 8, 11}, SEQ_ONLIST, "indrops_onlist2.txt" }, // cell barcode 2
 * 		//{ SD_R1, { 8, 11}, { 8,  8}, SEQ_RANDOM }, // umi
 * 		{ 0 }
 * 	}
 * },
 */


// auto *x = malloc(sizeof(struct library_layout));
// x.entries = malloc(sizeof(struct entry) * length);

// iCLIP
//   barcodes at start of sequence
//   ^cell barcode: 2 bp
//   + umi barcode: 3 bp
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
// bases 8-9 are a special pair with only 4 options
//
// 737K: (737,280 barcodes)
// [1-7]: 480 options, [8-9]: AG | GT | TC | CA, [10-16]: 384 options per prefix
// 3M: (6,794,880 barcodes)
// [1-7]: 960 options, [8-9]: AG|TC, [10-16]: 1920 options per prefix
//                     [8-9]: GT|CA, [10-16]: 1619 options per prefix
// prefix/suffix homopolymers runs can only be up to *3*,
// the fixed 2-mer breaks up longer homopolymers while allowing 4-mers
//     h/t Twelve Nue for analysis

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


// https://vectorbase.org/vectorbase/service/record-types/dfile/searches/GetFileRecordsByID/reports/zippedFiles


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
