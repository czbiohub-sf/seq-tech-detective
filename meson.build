project(
    'seq-detective',
    ['c', 'cpp'],
    version: '0.1.0',
    license: 'BSD3',
    default_options: [
        'buildtype=debugoptimized',
        'warning_level=3',
        'c_std=gnu23,gnu2x,c23,c2x',
    ],
)
exename = 'seq-detective-fp'
compiler = meson.get_compiler('c')

proj_args = [
    '-g3',
    '-Wno-gnu-binary-literal',  # clang-18 bug
]
if get_option('test').enabled()
    proj_args += [
        '-Wno-stringop-overread',  # intentional
        '-Wno-attributes',  # rexo
        '-Wno-format-extra-args',  # rexo
        '-Wno-clobbered',  # rexo
        '-Wno-unknown-warning-option',  # clang...
    ]
endif
add_project_arguments(proj_args, language: ['c'])

# dependencies: openmp
openmp_dep = dependency('openmp')
deps = [openmp_dep]

# conf
pkgdatadir = join_paths(
    [get_option('prefix'), get_option('datadir'), meson.project_name()],
)
conf = configuration_data()
conf.set_quoted('PACKAGE_NAME', meson.project_name())
conf.set_quoted('VERSION', meson.project_version())
conf.set_quoted('PKGDATADIR', join_paths(get_option('prefix'), pkgdatadir))
conf.set10('LOG_USE_COLOR', get_option('log_use_color'))
if compiler.has_function('posix_fadvise', prefix: '#include <fcntl.h>')
    conf.set10('HAVE_POSIX_FADVISE', true)
endif
configure_file(output: 'config.h', configuration: conf)

# sources
lib_src = files(
    'src/fastq.c',
    'src/filereader.c',
    'src/fingerprint_info.c',
    'src/log.c',  # rxi
    'src/table_builder.c',
)
main_src = files('src/main.c')
src = [main_src, lib_src]

seqdetective_headers = include_directories('.', 'include')
inc = [seqdetective_headers]

# technology fingerprint resources + shared object
subdir('resources')

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
    src,
    gnu_symbol_visibility: 'default',
    include_directories: inc,
    dependencies: deps,
    install: true,
)
# supporting scripts
subdir('scripts')


subdir('tests')
