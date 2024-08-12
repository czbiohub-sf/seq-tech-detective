specs = ['specs/inDropv2/spec.yaml', 'specs/10x-RNA-v2/spec.yaml']

converter = find_program('../scripts/seqspec2detective.py')
fingerprints_c = custom_target('fingerprints.c',
                               input: specs,
                               output: 'fingerprints.c',
                               command: [converter, '@INPUT@', '-fi', '-o', '@OUTPUT@']
                               )

libfingerprints = shared_library('fingerprints', [fingerprints_c],
                                 include_directories: inc)