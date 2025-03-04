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

# C options
compiler = meson.get_compiler('c')
proj_args = [
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

# Dependencies
openmp_dep = dependency('openmp')


# Conf
datadir     = join_paths(get_option('prefix'), get_option('datadir'))
bindir      = join_paths(get_option('prefix'), get_option('bindir'))
libdir      = join_paths(get_option('prefix'), get_option('libdir'))
libexecdir  = join_paths(get_option('prefix'), get_option('libexecdir'))
varcachedir = join_paths(get_option('prefix'), get_option('localstatedir'), 'cache')
varlibdir   = join_paths(get_option('prefix'), get_option('localstatedir'), 'lib')
pkgdatadir  = join_paths(datadir, meson.project_name())
pkglibdir   = join_paths(libdir, meson.project_name())
pkglibexecdir  = join_paths(libexecdir, meson.project_name())
pkgvarcachedir = join_paths(varcachedir, meson.project_name())
pkgvarlibdir   = join_paths(varlibdir, meson.project_name())

conf = configuration_data()
conf.set_quoted('PACKAGE_NAME', meson.project_name())
conf.set_quoted('VERSION', meson.project_version())
conf.set_quoted('PKGDATADIR', pkgdatadir)
conf.set_quoted('PKGLIBDIR', pkglibdir)
conf.set_quoted('PKGLIBEXECDIR', pkglibexecdir)
conf.set_quoted('PKGVARCACHEDIR', pkgvarcachedir)
conf.set_quoted('PKGVARLIBDIR', pkgvarlibdir)
conf.set10('LOG_USE_COLOR', get_option('log_use_color'))
if compiler.has_function('posix_fadvise', prefix: '#include <fcntl.h>')
    conf.set10('HAVE_POSIX_FADVISE', true)
endif

configure_file(output: 'config.h', configuration: conf)

# Headers
config_h_inc = include_directories('.')
fingerprint_inc = include_directories('include')
inc = [config_h_inc, fingerprint_inc]

# Sources
subdir('src')

# Technology fingerprint resources + shared object
subdir('resources')

# Supporting scripts
subdir('scripts')

# Tests
subdir('tests')
