project('seq-detective', 'c',
  version : '0.1.0',
  default_options : ['warning_level=3', 'c_std=gnu2x'])
add_project_arguments(['-fopenmp', '-gsplit-dwarf'], language : ['c'])
add_project_link_arguments(['-fopenmp'], language : ['c', 'cpp'])

main_src = files('src/main.c')

#tracy_dep = dependency('tracy', required: get_option('tracy'))
tracy_inc = include_directories('3rdparty/tracy')
tracy_src = files('3rdparty/tracy/public/TracyClient.cpp')

inc = []
src = [main_src]
exename = 'seq-detective'

if get_option('tracy').enabled()
    add_languages('cpp')
    add_project_arguments(['-DTRACY_ENABLE=1', '-DTRACY_NO_EXIT=1'],
                          language: ['c', 'cpp'])
    add_project_arguments(['-fno-omit-frame-pointer'],
                          language: ['c'])
    add_project_link_arguments(['-rdynamic', '-lstdc++'],
                               language : ['c'])
    add_project_link_arguments(['-lm', '-lstdc++', '-pthread', '-ldl'],
                               language : ['cpp'])
    src += tracy_src
    inc += tracy_inc
    exename = 'seq-detective-tracy'
endif

seq_detective = executable(exename,
                           src,
                           include_directories: inc)

#run_target('lint',
#           command : 'clang-tidy src/*.[ch] --header-filter=".*" -- -isystem /usr/lib/clang/16.0.6/include/ $(CLANG_CFLAGS)')
