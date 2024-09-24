#include <rexo.h>
#include <table_builder.h>

/*
 * RX_SET_UP(mock_onlist_rgn_set_up)
 * {
 * 	sd_fingerprint *mock_rgn = (sd_fingerprint *)RX_DATA;
 * 	mock_rgn->read = SD_R1;
 * 	mock_rgn->dir = SD_FWD;
 * 	mock_rgn->type = SD_ONLIST;
 * 	mock_rgn->len = (sd_range){0, 0};
 * 	mock_rgn->ofs  = (sd_range){16, 16};
 * 	mock_rgn->sequence = "cb_10x_737K-august-2016.txt";
 *
 * 	return RX_SUCCESS;
 * }
 * RX_FIXTURE(mock_fingerprint_fixture, sd_fingerprint, .set_up = mock_onlist_rgn_set_up);
 */

RX_SET_UP(mock_fixed_hits_set_up)
{
	sd_fp_hits *mock_fp_hits   = (sd_fp_hits *)RX_DATA;
	mock_fp_hits->name         = "AAGGCGTCACAAGCAATCACTC";
	mock_fp_hits->dir          = SD_REV;
	mock_fp_hits->type         = SD_FIXED;
	mock_fp_hits->id           = 0;
	mock_fp_hits->len          = (sd_range){22, 22};
	mock_fp_hits->seq_int      = seq_to_int("AAGGCGTCACAAGCAATCACTC", 22, 1);
	mock_fp_hits->ofs          = (sd_fp_ofs_node *)malloc(sizeof(sd_fp_ofs_node));
	mock_fp_hits->ofs->next    = NULL;
	mock_fp_hits->ofs->ofs.min = 8;
	mock_fp_hits->ofs->ofs.max = 11;

	return RX_SUCCESS;
}
RX_FIXTURE(mock_fp_hits_fixture, sd_fp_hits, .set_up = mock_fixed_hits_set_up);


RX_TEST_CASE(fp_hits, fixed_init, .fixture = mock_fp_hits_fixture)
{
	sd_fp_hits *data = (sd_fp_hits *)RX_DATA;

	RX_STR_REQUIRE_EQUAL("AAGGCGTCACAAGCAATCACTC", data->name);
	RX_PTR_REQUIRE_NOT_EQUAL(NULL, data->ofs);
	RX_INT_REQUIRE_EQUAL(8, data->ofs->ofs.min);
	RX_INT_REQUIRE_EQUAL(11, data->ofs->ofs.max);
}

RX_TEST_CASE(fp_hits, add_expected_ofs, .fixture = mock_fp_hits_fixture)
{
	sd_fp_hits *data = (sd_fp_hits *)RX_DATA;

	sd_fingerprint *mock_rgn = (sd_fingerprint *)malloc(sizeof(sd_fingerprint));
	mock_rgn->ofs            = (sd_range){16, 16};
	// update ofs only looks at ofs field
	update_expected_ofs(data, mock_rgn);

	RX_PTR_REQUIRE_NOT_EQUAL(NULL, data->ofs);
	RX_PTR_REQUIRE_NOT_EQUAL(NULL, data->ofs->next);
	RX_INT_REQUIRE_EQUAL(8, data->ofs->ofs.min);
	RX_INT_REQUIRE_EQUAL(11, data->ofs->ofs.max);
	RX_INT_REQUIRE_EQUAL(16, data->ofs->next->ofs.min);
	RX_INT_REQUIRE_EQUAL(16, data->ofs->next->ofs.max);
}


int main(int argc, const char **argv) { return rx_main(0, NULL, argc, argv) == RX_SUCCESS ? 0 : 1; }
