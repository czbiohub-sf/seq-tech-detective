#!/bin/bash

#SBATCH --job-name=seq-detective-scan
#SBATCH --array=0-249
#SBATCH --time=00:24:00
#SBATCH --partition=preempted
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --output=slurm.out/scan-%A-%a.out
#SBATCH --error=slurm.out/scan-%A-%a.err

# --array=0-249


module load mamba
mamba activate seq-detective

ACCESSION_FILE=accessions.txt
HISAT2_INDEX="${PWD}/hisat2-index/GCF_000002035.6_GRCz11_genomic"
GTF="${PWD}/ref/Danio-rerio_GRCz11/ncbi_dataset/data/GCF_000002035.6/GCF_000002035.6_GRCz11_genomic.fna"
workdir="$(mktemp -d)"

#random sleep based on job array index to avoid overloading the server
sleep $((SLURM_ARRAY_TASK_ID % (SLURM_ARRAY_TASK_COUNT / 2)))
readarray -t ACCESSIONS < accessions.txt

TASKSIZE=$(( ( ${#ACCESSIONS[@]} + SLURM_ARRAY_TASK_COUNT - 1 ) / SLURM_ARRAY_TASK_COUNT ))
START=$(( SLURM_ARRAY_TASK_ID * TASKSIZE ))
END=$(( START + TASKSIZE ))
TASK_OUTPUT="${PWD}/slurm.out/scan-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.tsv"

pushd "$workdir"

fastqdumpwithlimit() {
    ACCESSION=$1
    LIMIT=$2
    fastq-dump --split-3 $ACCESSION -X $LIMIT
    files=$($(ls -1 "$ACCESSION*"))
    echo $files
}

sam2fastq_cpus=$(( SLURM_CPUS_PER_TASK - 4 ))
[[ $sam2fastq_cpus -lt 1 ]] && sam2fastq_cpus=1
samdumpwithlimit() {
    ACCESSION=$1
    LIMIT=$(( $2 * 4 ))
    sam2fastq_param="-@ $sam2fastq_cpus -1 $ACCESSION.1.fastq.down -2 $ACCESSION.2.fastq.down -0 $ACCESSION.fastq.down"
    rm -f "${ACCESSION}.sampipe" "$ACCESSION.1.fastq.down" "$ACCESSION.2.fastq.down" "$ACCESSION.fastq.down"
    mkfifo "${ACCESSION}.sampipe"
    mkfifo $ACCESSION.1.fastq.down $ACCESSION.2.fastq.down $ACCESSION.fastq.down
    sam-dump $ACCESSION > "${ACCESSION}.sampipe" &
    samdump_pid=$!
    samtools fastq "${ACCESSION}.sampipe" $sam2fastq_param -T CB,UB,QX,CR,BC,QT &
    samtools_pid=$!
    echo "sam-dump pid: $samdump_pid $samtools_pid" 1>&2
    head -n $LIMIT $ACCESSION.1.fastq.down > $ACCESSION.1.fastq &
    head1_pid=$!
    head -n $LIMIT $ACCESSION.2.fastq.down > $ACCESSION.2.fastq &
    head2_pid=$!
    head -n $LIMIT $ACCESSION.fastq.down > $ACCESSION.fastq &
    head0_pid=$!
    ps 1>&2
    wait -n $head2_pid $head0_pid && kill $samdump_pid $samtools_pid $head1_pid $head2_pid $head0_pid
    rm "${ACCESSION}.sampipe" "$ACCESSION.1.fastq.down" "$ACCESSION.2.fastq.down" "$ACCESSION.fastq.down"
    # RETURNED MATES COULD BE LESS THAN LIMIT!
    # so find out if mates have more reads
    mate2_lines=$(wc -l "$ACCESSION.2.fastq" | cut -d' ' -f1)
    single_lines=$(wc -l "$ACCESSION.fastq" | cut -d' ' -f1)
    if [ "$mate2_lines" -ge "$single_lines" ]; then
        rm -f $ACCESSION.fastq
        echo "$ACCESSION.1.fastq" "$ACCESSION.2.fastq"
    else
        rm -f $ACCESSION.1.fastq $ACCESSION.2.fastq
        echo "$ACCESSION.fastq"
    fi
}

for idx in $(seq $START $END); do
    if [ $idx -ge ${#ACCESSIONS[@]} ]; then
        break
    fi
    ACCESSION=${ACCESSIONS[$idx]}
    
    echo "Processing $ACCESSION"
    types=$(efetch -db sra -format xml -id $ACCESSION | xtract -pattern RUN -group SRAFiles -if SRAFile@supertype -equals "Original" -tab " " -element @semantic_name)
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
        echo "Unknown file type: $types"
        files=$(fastqdumpwithlimit $ACCESSION 2000000)
        for file in $files; do
            seq-detective fingerprint-rough $file $HISAT2_INDEX $GTF | tee -a "${TASK_OUTPUT}"
            rm $file
        done
    fi
done

popd