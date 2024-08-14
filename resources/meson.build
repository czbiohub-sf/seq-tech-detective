fs = import('fs')

spec_dirs = ['specs/inDropv2/', 'specs/10x-RNA-v2/']
specs = []
onlists = []

# barcode data files
zstd = find_program('zstd')
foreach spec_dir : spec_dirs
    specs += join_paths(spec_dir, 'spec.yaml')
    onlist_zst = run_command(
        ['find', spec_dir, '-name', '*.zst'],
        capture: true,
        check: true,
    ).stdout()
    foreach f : onlist_zst.split('\n')
        if f.strip() != ''
            uncompressed = fs.stem(f.strip())
            run_command([zstd, '-d', f, '-o', uncompressed], check: false)
            fs.copyfile(uncompressed)
            onlists += uncompressed
        endif
    endforeach
endforeach

install_data(onlists)

if get_option('ext_specs').enabled()
# seqspec fingerprint data
    converter = find_program('../scripts/seqspec2detective.py')
    fingerprints_c = custom_target(
        'fingerprints.c',
        input: specs,
        output: 'fingerprints.c',
        command: [converter, '@INPUT@', '-fi', '-o', '@OUTPUT@'],
    )

    libfingerprints = shared_library(
        'fingerprints',
        [fingerprints_c],
        include_directories: inc,
        install: true,
    )
endif
