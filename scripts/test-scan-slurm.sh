#!/bin/bash

#SBATCH --job-name=seq-detective-scan
#SBATCH --array=0-179
#SBATCH --time=48:00:00
#SBATCH --partition=preempted
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --output=slurm.out/scan-%A-%a.out
#SBATCH --error=slurm.out/scan-%A-%a.err

module load mamba
mamba activate seq-detective

PATH="${PATH}:$(pwd -P)/seq-detective/"

ACCESSION_FILE=all_zf_transcriptomic.csv
HISAT2_INDEX="$(pwd -P)/hisat2-index/GCF_000002035.6_GRCz11_genomic"
GTF="$(pwd -P)/ref/Danio-rerio_GRCz11/ncbi_dataset/data/GCF_000002035.6/genomic.gtf"
workdir="$(mktemp -d)"

cleanup() {
	rm -r "${workdir}"
}
trap 'cleanup' INT TERM EXIT

# sleep based on job array index to avoid overloading the server
sleep "${SLURM_ARRAY_TASK_ID}"
readarray -t ACCESSIONS <"${ACCESSION_FILE}"

TASKSIZE=$(((${#ACCESSIONS[@]} + SLURM_ARRAY_TASK_COUNT - 1) / SLURM_ARRAY_TASK_COUNT))
START=$((SLURM_ARRAY_TASK_ID * TASKSIZE))
END=$((START + TASKSIZE))
TASK_OUTPUT="${PWD}/slurm.out/scan-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.tsv"

cd "${workdir}" || exit 1

for idx in $(seq "${START}" "${END}"); do
	if [ "${idx}" -ge ${#ACCESSIONS[@]} ]; then
		break
	fi
	ROW="${ACCESSIONS[$idx]}"
	ACCESSION=$(cut -d ',' -f1 <(echo "$ROW"))
	types=$(cut -d ',' -f2 <(echo "$ROW") | tr -d '\r')

	echo "Processing ${ACCESSION} (${types})"
	files=$(seq-detective-download -X 2000000 -b "${ACCESSION}" "${types}")
	for file in $files; do
		seq-detective fingerprint-rough "${file}" "${HISAT2_INDEX}" "${GTF}" | tee -a "${TASK_OUTPUT}"
		rm "${file}"
	done
done

ls 1>&2
