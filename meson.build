project(
    'seq-detective',
    ['c', 'cpp'],
    version: '0.1.0',
    license: 'BSD3',
    default_options: ['buildtype=release', 'warning_level=3', 'c_std=gnu2x'],
)
exename = 'seq-detective'

add_project_arguments(['-fopenmp', '-gsplit-dwarf'], language: ['c'])
add_project_link_arguments(['-fopenmp'], language: ['c', 'cpp'])

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
configure_file(output: 'config.h', configuration: conf)

# sources
main_src = files(
    'src/fastq.c',
    'src/filereader.c',
    'src/main.c',
    'src/table_builder.c',
)
src = [main_src]

seqdetective_headers = include_directories('.', 'include')
inc = [seqdetective_headers]

# shared object
if get_option('ext_specs').enabled()
    subdir('resources')
endif

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

seq_detective = executable(
    exename,
    src,
    gnu_symbol_visibility: 'default',
    include_directories: inc,
    dependencies: deps,
    install: true,
)

#if get_option('test')
#    subdir('test')
#endif
