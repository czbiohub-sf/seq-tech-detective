#!/bin/bash

#SBATCH --job-name=seq-detective-scan
#SBATCH --array=0-249
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
  rm -r "$workdir"
}
trap 'cleanup' SIGINT SIGTERM EXIT

# sleep based on job array index to avoid overloading the server
sleep $SLURM_ARRAY_TASK_ID
readarray -t ACCESSIONS < "${ACCESSION_FILE}"

TASKSIZE=$(( ( ${#ACCESSIONS[@]} + SLURM_ARRAY_TASK_COUNT - 1 ) / SLURM_ARRAY_TASK_COUNT ))
START=$(( SLURM_ARRAY_TASK_ID * TASKSIZE ))
END=$(( START + TASKSIZE ))
TASK_OUTPUT="${PWD}/slurm.out/scan-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.tsv"

cd "$workdir"

fastqdumpwithlimit() {
    ACC=$1
    LIMIT=$2
    fastq-dump --split-3 $ACC -X $LIMIT 1>&2
    files=$( echo $ACC* )
    echo $files
}

sam2fastq_cpus=$(( SLURM_CPUS_PER_TASK - 4 ))
[[ $sam2fastq_cpus -lt 1 ]] && sam2fastq_cpus=1
samdumpwithlimit() {
    ACC=$1
    LIMIT=$(( $2 * 4 ))
    sam2fastq_param="-@ $sam2fastq_cpus -1 $ACC.1.fastq.down -2 $ACC.2.fastq.down -0 $ACC.fastq.down
    rm -f "${ACC}.sampipe" "$ACC.1.fastq.down" "$ACC.2.fastq.down" "$ACC.fastq.down"
    mkfifo "${ACC}.sampipe"
    mkfifo $ACC.1.fastq.down $ACC.2.fastq.down $ACC.fastq.down
    sam-dump $ACC > "${ACC}.sampipe" &
    samdump_pid=$!
    samtools fastq "${ACC}.sampipe" $sam2fastq_param -T CB,UB,QX,CR,BC,QT &
    samtools_pid=$!
    echo "sam-dump pid: $samdump_pid $samtools_pid" 1>&2
    head -n $LIMIT $ACC.1.fastq.down > $ACC.1.fastq &
    head1_pid=$!
    head -n $LIMIT $ACC.2.fastq.down > $ACC.2.fastq &
    head2_pid=$!
    head -n $LIMIT $ACC.fastq.down > $ACC.fastq &
    head0_pid=$!
    ps 1>&2
    wait -n $head2_pid $head0_pid && kill $samdump_pid $samtools_pid $head1_pid $head2_pid $head0_pid
    rm "${ACC}.sampipe" "$ACC.1.fastq.down" "$ACC.2.fastq.down" "$ACC.fastq.down"
    # RETURNED MATES COULD BE LESS THAN LIMIT!
    # so find out if mates have more reads
    mate2_lines=$(wc -l "$ACC.2.fastq" | cut -d' ' -f1)
    single_lines=$(wc -l "$ACC.fastq" | cut -d' ' -f1)
    if [ "$mate2_lines" -ge "$single_lines" ]; then
        rm -f $ACC.fastq
        echo "$ACC.1.fastq" "$ACC.2.fastq"
    else
        rm -f $ACC.1.fastq $ACC.2.fastq
        echo "$ACC.fastq"
    fi
}

for idx in $(seq $START $END); do
    if [ $idx -ge ${#ACCESSIONS[@]} ]; then
        break
    fi
    ROW="${ACCESSIONS[$idx]}"
    ACCESSION=$( cut -d ',' -f1 <(echo "$ROW") )
    types=$( cut -d ',' -f2 <(echo "$ROW") | tr -d '\r' )

    echo "Processing $ACCESSION ($types)"
    if [[ $types == *"fastq"* ]]; then
        # one or more fastq mates, eg SRR24043286
        files=$(fastqdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    elif [[ $types == *"10X Genomics bam file"* ]]; then
        # 10X Genomics bam file, eg SRR17117610
        # seq-detective doesn't try to handle 10x genomics bam files with bc in tags
        files=$(samdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    elif [[ $types == *"bam"* ]]; then
        # bam file, eg ERR1251894
        files=$(samdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    elif [[ $types == *"cram"* ]]; then
        # cram file, eg ERR2788340
        files=$(samdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    else
        # unknown file type, try dumping as fastq
        echo "Unknown file type: $types" 1>&2
        files=$(fastqdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    fi
done

ls 1>&2