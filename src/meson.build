exename = 'seq-detective-fp'

fingerprint_lib_src = files(
    'fastq.c',
    'filereader.c',
    'fingerprint_info.c',
    'log.c',  # rxi
    'table_builder.c',
)
fingerprint_main_src = files('main.c')
fingerprint_src = [fingerprint_main_src, fingerprint_lib_src]

deps = [openmp_dep]

if get_option('tracy').enabled()
    exename = 'seq-detective-tracy'
    tracy_dep = dependency(
        'tracy',
        static: true,
        default_options: ['warning_level=0', 'tracy:no_exit=true'],
    )
    deps += [tracy_dep]

    add_project_arguments(['-DTRACY_ENABLE=1'], language: ['c', 'cpp'])
    add_project_arguments(['-fno-omit-frame-pointer'], language: ['c'])
    add_project_link_arguments(['-rdynamic', '-lstdc++'], language: ['c'])
    add_project_link_arguments(['-ldl'], language: ['c', 'cpp'])

    if get_option('buildtype') != 'debugoptimized'
        warning('Profiling builds should set --buildtype=debugoptimized')
    endif
endif


seq_detective_fp = executable(
    exename,
    fingerprint_src,
    gnu_symbol_visibility: 'default',
    include_directories: inc,
    dependencies: deps,
    install: true,
    build_by_default: true,
)
