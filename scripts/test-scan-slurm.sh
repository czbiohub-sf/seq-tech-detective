#!/bin/bash

#SBATCH --job-name=seq-detective-scan
#SBATCH --array=0-74108
#SBATCH --time=48:00:00
#SBATCH --partition=preempted
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --output=slurm.out/log/scan-%A-%a.log
#SBATCH --error=slurm.out/log/scan-%A-%a.log
#SBATCH --open-mode=append
CHECKPOINT="${PWD}/slurm.out/scan-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.checkpoint"
JSON_OUT="${PWD}/slurm.out/scan-${SLURM_ARRAY_JOB_ID}.json"

module load mamba
mamba activate seq-detective

PATH="${PATH}:$(pwd -P)/seq-detective/"

ACCESSION_FILE=accession_data_for_scan.csv
HISAT2_INDEX="$(pwd -P)/ref/hisat2-index/GCF_000002035.6_GRCz11_genomic"
GTF="$(pwd -P)/ref/Danio-rerio_GRCz11/ncbi_dataset/data/GCF_000002035.6/genomic.gtf"

readarray -t ACCESSIONS <"${ACCESSION_FILE}"
TASKSIZE=$(((${#ACCESSIONS[@]} + SLURM_ARRAY_TASK_COUNT - 1) / SLURM_ARRAY_TASK_COUNT))
START=$((SLURM_ARRAY_TASK_ID * TASKSIZE))
END=$((START + TASKSIZE - 1))

READLIMIT=200000

workdir="$(mktemp -d)"
cd "${workdir}" || exit 1

cleanup() {
	rm -r "${workdir}"
}
trap 'cleanup' INT TERM EXIT

# random sleep to avoid overloading the server
jobc=$(squeue --me -t R -h -O jobid | wc -l)
echo "sleeping $(((RANDOM % jobc) / 5))" >&2
sleep $(((RANDOM % jobc) / 5))

# format a json key-value pair
# $1: key
# $2: value
json_kv() {
	printf '"%s": %s' "${1}" "${2}"
}

NL=$'\n'
if [[ -e "${CHECKPOINT}" ]]; then
	START=$(cat "${CHECKPOINT}")
#else
#	echo "[" >>"${JSON_OUT}"
fi
for idx in $(seq "${START}" "${END}"); do
	if [ "${idx}" -ge ${#ACCESSIONS[@]} ]; then
		break
	fi
	ROW="${ACCESSIONS[$idx]}"
	ACCESSION=$(cut -d ',' -f1 <(echo "$ROW"))
	types=$(cut -d ',' -f2 <(echo "$ROW") | tr -d '\r')

	echo "Processing ${ACCESSION} (${types})" >&2
	# open accession block
	json="{\"accession\": \"${ACCESSION}\","
	json="${json}\"readfiles\": [${NL}"
	files=$(seq-detective-download -X "${READLIMIT}" -c $((SLURM_CPUS_PER_TASK - 1)) -b "${ACCESSION}" "${types}")
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
	flock -x "${JSON_OUT}" printf "%s" "${json}" >>"${JSON_OUT}"
	echo $((idx + 1)) >"${CHECKPOINT}"
done
# close json
#echo "]" >>"${JSON_OUT}"

rm "${CHECKPOINT}"
ls 1>&2
