if get_option('test').enabled()
    rexo = dependency(
        'rexo',
        default_options: ['c_args=-Wno-clobbered'],
        static: true,
    )

    seqtoint_tests_exe = executable(
        'seqtoint-tests',
        ['seqtoint-test.c', lib_src],
        include_directories: inc,
        dependencies: [rexo],
    )
    test('seqtoint tests', seqtoint_tests_exe)

    table_tests_exe = executable(
        'tablebuilder-tests',
        ['table-builder-test.c', lib_src],
        include_directories: inc,
        dependencies: [rexo],
    )
    test('table_builder tests', table_tests_exe)
endif
