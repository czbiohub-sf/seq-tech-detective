#include <rexo.h>
#include <table_builder.h>

// A       [       0]
// AC      [      10]
// ACT     [     210]
// ACTG    [    3210] 0b11100100

// Reverse Complement:

// A       [       2]
// AC      [      23]
// ACT     [     230]
// ACTG    [    2301] 0b10110001

RX_TEST_SUITE(seq_to_int_16);
#define SEQ_EQUAL16(i, sq)                                                                         \
	RX_TEST_CASE(seq_to_int_16, sq)                                                                \
	{                                                                                              \
		const char *seq = #sq;                                                                     \
		RX_INT_REQUIRE_EQUAL_MSG(                                                                  \
			i, seq_to_int16_s(seq, strlen(seq)), "%s: %o", seq, seq_to_int16_s(seq, strlen(seq))); \
	}

RX_TEST_SUITE(seq_to_int_32);
#define SEQ_EQUAL32(i, sq)                                                                         \
	RX_TEST_CASE(seq_to_int_32, sq)                                                                \
	{                                                                                              \
		const char *seq = #sq;                                                                     \
		RX_INT_REQUIRE_EQUAL_MSG(                                                                  \
			i, seq_to_int32_s(seq, strlen(seq)), "%s: %o", seq, seq_to_int32_s(seq, strlen(seq))); \
	}

RX_TEST_SUITE(seq_to_int);
#define SEQ_EQUAL(i, sq)                                                         \
	RX_TEST_CASE(seq_to_int, sq)                                                 \
	{                                                                            \
		const char *seq = #sq;                                                   \
		const int   len = strlen(seq);                                           \
		RX_INT_REQUIRE_EQUAL_MSG(                                                \
			i, seq_to_int(seq, len, 0), "%s: %o", seq, seq_to_int(seq, len, 0)); \
	}

RX_TEST_SUITE(seq_to_int_rc);
#define SEQ_EQUAL_RC(i, sq)                                                      \
	RX_TEST_CASE(seq_to_int_rc, sq)                                              \
	{                                                                            \
		const char *seq = #sq;                                                   \
		const int   len = strlen(seq);                                           \
		RX_INT_REQUIRE_EQUAL_MSG(                                                \
			i, seq_to_int(seq, len, 1), "%s: %o", seq, seq_to_int(seq, len, 1)); \
	}


// 16 bit (8bp)
SEQ_EQUAL16(0b0000000000000000, AAAAAAAA)
SEQ_EQUAL16(0b0101010101010101, CCCCCCCC)
SEQ_EQUAL16(0b1010101010101010, TTTTTTTT)
SEQ_EQUAL16(0b1111111111111111, GGGGGGGG)
SEQ_EQUAL16(0b1011010011000110, TCAGACGT)

// partial sequences
SEQ_EQUAL16(0b00000000000000, AAAAAAA)
SEQ_EQUAL16(0b11111111111111, GGGGGGG)
SEQ_EQUAL16(0b11100100, ACTG)
SEQ_EQUAL16(0b101010, TTT)

SEQ_EQUAL16(0b00, A)
SEQ_EQUAL16(0b01, C)
SEQ_EQUAL16(0b10, T)
SEQ_EQUAL16(0b11, G)

// 32bit (16bp)
SEQ_EQUAL32(0b00000000000000000000000000000000, AAAAAAAAAAAAAAAA)
SEQ_EQUAL32(0b01010101010101010101010101010101, CCCCCCCCCCCCCCCC)
SEQ_EQUAL32(0b10101010101010101010101010101010, TTTTTTTTTTTTTTTT)
SEQ_EQUAL32(0b11111111111111111111111111111111, GGGGGGGGGGGGGGGG)
SEQ_EQUAL32(0b11100100111001001110010011100100, ACTGACTGACTGACTG)

// partial sequences
SEQ_EQUAL32(0b000000000000000000000000000000, AAAAAAAAAAAAAAA)
SEQ_EQUAL32(0b111111111111111111111111111111, GGGGGGGGGGGGGGG)

// 9bp sequences to seq_to_int32 is nonfatal contract violation
RX_TEST_CASE(seq_to_int_32, ACTG)
{
	const char    *A16     = "ACTG";
	const uint32_t A16_int = seq_to_int32_s(A16, 4);
	RX_INT_CHECK_EQUAL_MSG(0b11100100, A16_int, "seq: %o", A16_int);
}
RX_TEST_CASE(seq_to_int_32, T)
{
	const char    *A16     = "T";
	const uint32_t A16_int = seq_to_int32_s(A16, 1);
	RX_INT_CHECK_EQUAL_MSG(0b10, A16_int, "seq: %o", A16_int);
}
RX_TEST_CASE(seq_to_int_32, A)
{
	const char    *A16     = "A";
	const uint32_t A16_int = seq_to_int32_s(A16, 1);
	RX_INT_CHECK_EQUAL_MSG(0b00, A16_int, "seq: %o", A16_int);
}
RX_TEST_CASE(seq_to_int_32, C)
{
	const char    *A16     = "C";
	const uint32_t A16_int = seq_to_int32_s(A16, 1);
	RX_INT_CHECK_EQUAL_MSG(0b01, A16_int, "seq: %o", A16_int);
}
RX_TEST_CASE(seq_to_int_32, G)
{
	const char    *A16     = "G";
	const uint32_t A16_int = seq_to_int32_s(A16, 1);
	RX_INT_CHECK_EQUAL_MSG(0b11, A16_int, "seq: %o", A16_int);
}


// width dispatch wrapper
SEQ_EQUAL(0b00, A)
SEQ_EQUAL(0b01, C)
SEQ_EQUAL(0b10, T)
SEQ_EQUAL(0b11, G)
SEQ_EQUAL(0b11100100, ACTG)
SEQ_EQUAL(0b1110010011100100, ACTGACTG)
SEQ_EQUAL(0b111001001110010011100100, ACTGACTGACTG)
SEQ_EQUAL(0b11100100111001001110010011100100, ACTGACTGACTGACTG)

// reverse complement
SEQ_EQUAL_RC(0b10, A)
SEQ_EQUAL_RC(0b11, C)
SEQ_EQUAL_RC(0b00, T)
SEQ_EQUAL_RC(0b01, G)
SEQ_EQUAL_RC(0b10110001, ACTG)
SEQ_EQUAL_RC(0b1011000110110001, ACTGACTG)
SEQ_EQUAL_RC(0b101100011011000110110001, ACTGACTGACTG)
SEQ_EQUAL_RC(0b10110001101100011011000110110001, ACTGACTGACTGACTG)


// bitpacked seq to string
RX_TEST_CASE(int64_to_seq, ACTG)
{
	const char    *A32     = "ACTGACTGACTGACTG";
	const uint64_t A32_int = seq_to_int32_s(A32, 16);
	char          *A32_str = int64_to_seq(A32_int);
	RX_STR_CHECK_EQUAL("ACTGACTGACTGACTGAAAAAAAAAAAAAAAA", A32_str);
	A32_str[16] = '\0';
	RX_STR_REQUIRE_EQUAL("ACTGACTGACTGACTG", A32_str);
}

RX_TEST_CASE(int64_to_seq, ACTG_rc)
{
	const char    *A32     = "ACTGACTGACTGACTG";
	const uint64_t A32_int = seq_to_int32_rc_s(A32, 16);
	char          *A32_str = int64_to_seq(A32_int);
	RX_STR_CHECK_EQUAL("CAGTCAGTCAGTCAGTAAAAAAAAAAAAAAAA", A32_str);
	A32_str[16] = '\0';
	RX_STR_REQUIRE_EQUAL("CAGTCAGTCAGTCAGT", A32_str);
}


int main(int argc, const char **argv) { return rx_main(0, NULL, argc, argv) == RX_SUCCESS ? 0 : 1; }
