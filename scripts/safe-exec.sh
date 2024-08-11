# fastq, yaml

fastq=$1
yaml=$2

:> specs.c
python scripts/seqspec2detective.py $yaml -i -f >> specs.c
cc -c -fpic specs.c -Iinclude -o specs.o
cc -shared -o specs.so specs.o
md5=$(md5sum specs.so)

seq-detective $fastq --specs-md5 "$md5"