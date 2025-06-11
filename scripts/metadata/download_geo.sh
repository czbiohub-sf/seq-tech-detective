#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <all_zf_listofGSEids.tsv>"
  exit 1
fi

listfile="$1"

## command is ./download_geo.sh all_zf_listofGSEids.tsv
## output is all_geo_families.xml

# create a date‐stamped download directory (YYYYMMDD)
today="$(date +'%Y%m%d')"
download_dir="GEO_downloads_${today}"
logfile="$download_dir/download.log"

# 0) Prepare download directory & log
echo "→ Preparing download directory: $download_dir"
mkdir -p "$download_dir"
echo "===== Download log started: $(date +"%Y-%m-%d %H:%M:%S") =====" > "$logfile"

# 1) Download loop (logs both to console and $logfile)
echo
echo "→ Downloading .tgz files into $download_dir (log: $logfile)"
while IFS=$'\t' read -r acc _; do
  [[ -z "$acc" || "$acc" =~ ^# ]] && continue

  prefix="${acc/%[0-9][0-9][0-9]/nnn}"
  url="https://ftp.ncbi.nlm.nih.gov/geo/series/${prefix}/${acc}/miniml/${acc}_family.xml.tgz"

  ts="$(date +"%Y-%m-%dT%H:%M:%S%z")"
  echo "[$ts] → Downloading $acc" | tee -a "$logfile"

  if wget -c --tries=3 --timeout=30 -P "$download_dir" "$url" >>"$logfile" 2>&1; then
    echo "[$ts]    SUCCESS: $acc" >> "$logfile"
  else
    echo "[$ts]    ERROR:   failed to download $acc" | tee -a "$logfile" >&2
    continue
  fi
done < "$listfile"

# 2) Extract all the .xml.tgz files
echo
echo "→ Extracting .xml files in $download_dir"
for tgz in "$download_dir"/*_family.xml.tgz; do
  echo "   • $tgz"
  tar -xzf "$tgz" -C "$download_dir"
done

# 3) Concatenate into one big XML inside $download_dir
combined="all_geo_families.xml"
echo
echo "→ Building combined XML: $combined"

{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<GEOFamilies>'
  for xml in "$download_dir"/*_family.xml; do
    echo "   • Adding $xml"
    sed '1d' "$xml"
  done
  echo '</GEOFamilies>'
} > "$combined"

# 4) Cleanup with awk, producing a cleaned XML
cleaned="all_geo_families_cleaned.xml"
echo
echo "→ Cleaning up protocol sections into: $cleaned"
awk '
  # — Data-Processing block —
  /<Data-Processing>/ {
    print
    in_dp = 1
    dp_buf = ""
    next
  }
  in_dp && /<\/Data-Processing>/ {
    printf "%s</Data-Processing>\n", dp_buf
    in_dp = 0
    next
  }
  in_dp {
    gsub(/\r/, "")
    gsub(/^[ \t]+|[ \t]+$/, "")
    dp_buf = dp_buf $0 " "
    next
  }

  # — Extract-Protocol block —
  /<Extract-Protocol>/ {
    print
    in_ep = 1
    ep_buf = ""
    next
  }
  in_ep && /<\/Extract-Protocol>/ {
    printf "%s</Extract-Protocol>\n", ep_buf
    in_ep = 0
    next
  }
  in_ep {
    gsub(/\r/, "")
    gsub(/^[ \t]+|[ \t]+$/, "")
    ep_buf = ep_buf $0 " "
    next
  }

  # — Growth-Protocol block —
  /<Growth-Protocol>/ {
    print
    in_gp = 1
    gp_buf = ""
    next
  }
  in_gp && /<\/Growth-Protocol>/ {
    printf "%s</Growth-Protocol>\n", gp_buf
    in_gp = 0
    next
  }
  in_gp {
    gsub(/\r/, "")
    gsub(/^[ \t]+|[ \t]+$/, "")
    gp_buf = gp_buf $0 " "
    next
  }

  # — Treatment-Protocol block —
  /<Treatment-Protocol>/ {
    print
    in_tp = 1
    tp_buf = ""
    next
  }
  in_tp && /<\/Treatment-Protocol>/ {
    printf "%s</Treatment-Protocol>\n", tp_buf
    in_tp = 0
    next
  }
  in_tp {
    gsub(/\r/, "")
    gsub(/^[ \t]+|[ \t]+$/, "")
    tp_buf = tp_buf $0 " "
    next
  }

  # — all other lines —
  { print }
' "$combined" > "$cleaned"

# 5) Summary
echo
echo "✅  Done!"
echo "   • Downloads logged to:          $logfile"
echo "   • Downloaded archives:          $(ls -1 "$download_dir"/*_family.xml.tgz 2>/dev/null | wc -l)"
echo "   • Extracted XML files:          $(ls -1 "$download_dir"/*_family.xml 2>/dev/null | wc -l)"
echo "   • Combined XML file path:       $combined"
echo "   • Cleaned XML file path:        $cleaned"
