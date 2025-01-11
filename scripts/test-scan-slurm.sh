#!/bin/bash

#SBATCH --job-name=seq-detective-scan
#SBATCH --array=0-1
#SBATCH --time=48:00:00
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --output=test.out/scan-%A-%a.out
#SBATCH --error=test.out/scan-%A-%a.err

module load mamba
mamba activate seq-detective

PATH="${PATH}:$(pwd -P)/seq-detective/"

ACCESSION_FILE=test.csv # accession_data_for_scan.csv
HISAT2_INDEX="$(pwd -P)/ref/hisat2-index/GCF_000002035.6_GRCz11_genomic"
GTF="$(pwd -P)/ref/Danio-rerio_GRCz11/ncbi_dataset/data/GCF_000002035.6/genomic.gtf"

readarray -t ACCESSIONS <"${ACCESSION_FILE}"
TASKSIZE=$(((${#ACCESSIONS[@]} + SLURM_ARRAY_TASK_COUNT - 1) / SLURM_ARRAY_TASK_COUNT))
START=$((SLURM_ARRAY_TASK_ID * TASKSIZE))
END=$((START + TASKSIZE))
TASK_OUTPUT="${PWD}/test.out/scan-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.json"

workdir="$(mktemp -d)"
cd "${workdir}" || exit 1

cleanup() {
	rm -r "${workdir}"
}
trap 'cleanup' INT TERM EXIT

# sleep based on job array index to avoid overloading the server
sleep "${SLURM_ARRAY_TASK_ID}"

# format a json key-value pair
# $1: key
# $2: value
json_kv() {
	printf '"%s": %s' "${1}" "${2}"
}

NL=$'\n'
echo "[" | tee -a "${TASK_OUTPUT}"
for idx in $(seq "${START}" "${END}"); do
	if [ "${idx}" -ge ${#ACCESSIONS[@]} ]; then
		break
	fi
	ROW="${ACCESSIONS[$idx]}"
	ACCESSION=$(cut -d ',' -f1 <(echo "$ROW"))
	types=$(cut -d ',' -f2 <(echo "$ROW") | tr -d '\r')

	echo "Processing ${ACCESSION} (${types})"
	# open accession block
	json="{\"accession\": \"${ACCESSION}\","
	json="${json}\"readfiles\": [${NL}"
	files=$(seq-detective-download -X 200000 -c $(( SLURM_CPUS_PER_TASK - 1 )) -b "${ACCESSION}" "${types}")
	first=1
	for file in ${files}; do
		# array item per file
		[ ${first} -ne 1 ] && json="${json},${NL}"
		f_res=$(seq-detective core "${file}" "${HISAT2_INDEX}" "${GTF}")
		json="${json}${f_res}"
		rm "${file}"
		first=0
	done
	# close accession block
	if [ "${idx}" -lt "${END}" ]; then
		json="${json}${NL}]},${NL}"
	else
		json="${json}${NL}]}${NL}"
	fi
	printf "%s" "${json}" | tee -a "${TASK_OUTPUT}"
done
# close json
echo "]" | tee -a "${TASK_OUTPUT}"

ls 1>&2
