#include <log.h>
#include <rexo.h>

#include "fastq.h"
#include "filereader.h"
#include "table_builder.h"

struct fixture_data {
	sd_fp_hits **fp_hits;
};
sd_fp_hits **FINGERPRINTS = NULL;
// RX_SET_UP(fp_table_set_up)
// {
// 	struct fixture_data *data       = (struct fixture_data *)RX_DATA;
//     data->fp_hits       = load_fingerprints();

// 	return RX_SUCCESS;
// }
// RX_FIXTURE(fp_hits_fixture, struct fixture_data, .set_up = fp_table_set_up);

sd_fp_hits *get_hits_by_name(sd_fp_hits **fp_hits, const char *name)
{
	for (; *fp_hits != NULL; ++fp_hits)
		if (strcmp((*fp_hits)->name, name) == 0)
			return *fp_hits;
	return NULL;
}

RX_TEST_CASE(fp_hits, _10x_RNA_v2_R1)
{
	char fq_buf[] =
		"@gnl|SRA|SRR27321692.1.1NS500762:212:HJ2HWBGX7:1:11101:25045:1053 Biological "
		"(Biological)\n"
		"ACGCCGAGTCGAAAGCGTAATGTTCT\n"
		"+\n"
		"??????????????????????????\n";
	const int  buf_len = strlen(fq_buf);
	FILE      *in      = fmemopen(fq_buf, buf_len, "r");
	struct res result  = fq_fread(in, FINGERPRINTS);

	// basic checks
	RX_INT_REQUIRE_EQUAL(26, result.len_reads);
	RX_INT_REQUIRE_EQUAL(1, result.num_reads);

	// check 10x fingerprints
	sd_fp_hits *hit = get_hits_by_name(result.fp_hits, "cb_10x_737K-august-2016.txt");
	RX_INT_REQUIRE_EQUAL(1, hit->hits[0]); // bc at position 0
}

RX_TEST_CASE(fp_hits, inDropv2)
{
	char fq_buf[] =
		"@gnl|SRA|SRR24918336.4995.1A01177:105:HHFHTDSX5:1:1101:25265:10614 Biological "
		"(Biological)\n"
		"TGATAACCCGTGAGTGATTGCTTGTGACGCCTTAGCTATGAACATAATCAGGAGTGAGATCGGAAGAGCACACGTCTGAACTCCAGTCAC"
		"GGACTTGGATCTCGTATGACCTGTTAATAGTTAAAAAAGAGGGGGGGGGGGGGGGGGGGGG\n"
		"+\n"
		"??????????????????????????????????????????????????????????????????????????????????????????"
		"?????????????????????????????????????????????????????????????\n";
	const int  buf_len = strlen(fq_buf);
	FILE      *in      = fmemopen(fq_buf, buf_len, "r");
	struct res result  = fq_fread(in, FINGERPRINTS);

	// basic checks
	RX_INT_REQUIRE_EQUAL(151, result.len_reads);
	RX_INT_REQUIRE_EQUAL(1, result.num_reads);

	// check 10x fingerprints
	sd_fp_hits *hit = get_hits_by_name(result.fp_hits, "cb_indrop_bc1.txt_RC");
	RX_UINT_REQUIRE_LESSER_OR_EQUAL(0, hit->hits[0]);  // bc at position 0
	hit = get_hits_by_name(result.fp_hits, "AAGGCGTCACAAGCAATCACTC_RC");
	RX_UINT_REQUIRE_LESSER_OR_EQUAL(0, hit->hits[11]); // rc of linker at position 11
	hit = get_hits_by_name(result.fp_hits, "cb_indrop_bc2.txt_RC");
	RX_UINT_REQUIRE_LESSER_OR_EQUAL(0, hit->hits[33]); // bc2 at position 33
}


int main(int argc, const char **argv)
{
	log_set_level(LOG_WARN);
	FINGERPRINTS = load_fingerprints();
	log_set_quiet(LOG_INFO);
	return rx_main(0, NULL, argc, argv) == RX_SUCCESS ? 0 : 1;
}
