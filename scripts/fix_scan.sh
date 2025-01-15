#!/bin/bash

DIR="${1}"
ext="${2:-.json}"

echo "["
first=1
for subf in "${DIR}"/*"${ext}"; do
	echo "${subf}" >&2
	if [ ${first} -ne 1 ]; then echo ","; fi
	# the job may have restarted, ignore earlier attempts
	start_line=$(grep -n "^\[$" "${subf}" | tail -n1 | cut -d ":" -f1)
	# skip opening bracket
	tail -n+$((start_line + 1)) "${subf}" | sed -z 's/},\n]/}\n]/g' | head -n-1 | sed -E 's/: ?,/: null,/g' | sed 's/: }/: null}/g' | sed -z 's/}\n{/},\n{/g'
	first=0
done
echo "]"
