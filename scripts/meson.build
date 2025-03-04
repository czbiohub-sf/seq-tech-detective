# supporting scripts

# safe-exec.sh
# seqspec2detective.py
# metadata-annotate.py
user_scripts = [
  'seq-detective'
]

# zebrafish-metadata.sh
# scan-slurm.sh
internal_scripts = [
  'index-build',
  'assembly-search',
  'seq-detective-download',
  'seq-detective-fingerprint',
  'seq-detective-map',
]


SCRIPT_PREPROCESS = find_program(configure_file(
  input : join_paths(meson.project_source_root(), 'build-aux/edit-script.sh.in'),
  output : 'edit-script.sh',
  configuration : conf))

foreach script : user_scripts
  custom_target(script,
                input : script + '.in',
                output : script,
                command : [SCRIPT_PREPROCESS, '@INPUT@', '@OUTPUT@'],
                install : true,
                install_dir : bindir,
                install_mode : 'rwxr-xr-x',
                install_tag : 'runtime',
                build_by_default : true
               )  
endforeach


foreach script : internal_scripts
  custom_target(script,
                input : script + '.in',
                output :  script,
                command : [SCRIPT_PREPROCESS, '@INPUT@', '@OUTPUT@'],
                install : true,
                install_dir : pkglibexecdir,
                install_mode : 'rwxr-xr-x',
                install_tag : 'runtime',
                build_by_default : true
               )
endforeach

# test(
# 	'seqspec-convert',
# 	'seqspec2detective.py',
# 	args: '../resource/specs/inDropv2/spec.yaml -i -f',
# 	protocol: 'exitcode')

# test(
# 	'seqspec-convert-exec',
# 	'safe-exec.sh',
# 	args: '../resource/specs/inDropv2/spec.yaml',
