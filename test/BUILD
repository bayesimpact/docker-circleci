py_test(
    name = 'test',
    deps = [
        ':get_demo_vars_test',
        ':ping_reviewers_test',
        ':simple_bazel_test',
    ])
py_test(
    name = 'get_demo_vars_test',
    srcs = ['get_demo_vars_test.py'],
    deps = ['//bin:get_demo_vars'],
)

py_test(
    name = 'ping_reviewers_test',
    srcs = ['ping_reviewers_test.py'],
    deps = ['//bin:ping_reviewers'],
)

py_test(
    name = 'simple_bazel_test',
    srcs = ['simple_bazel_test.py'],
    deps = ['//bin:simple_bazel'],
)
