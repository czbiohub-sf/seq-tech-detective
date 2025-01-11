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
        dependencies: [rexo, deps],
    )
    test('seqtoint tests', seqtoint_tests_exe)

    table_tests_exe = executable(
        'tablebuilder-tests',
        ['table-builder-test.c', lib_src],
        include_directories: inc,
        dependencies: [rexo, deps],
    )
    test('table_builder tests', table_tests_exe)

    detection_tests_exe = executable(
        'detection-tests',
        ['detection-test.c', lib_src],
        include_directories: inc,
        dependencies: [rexo, deps],
    )
    test('synthetic detection tests', detection_tests_exe)
endif
