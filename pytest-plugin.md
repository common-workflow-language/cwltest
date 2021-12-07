Switching to pytest plugin from cwltest

```
cwltest --test path/to/conformance_test_whatever.yaml --tool my-cwl-runner

# becomes

pytest path/to/conformance_test_whatever.yaml --cwl-runner my-cwl-runner
```

For the cwltest plugin to pytest to work, the CWL test file must start with `conformance_test`
and end with `.yaml` or `.yml`

`--cwl-runner` is optional, it defaults to "cwl-runner"
(which is typically a symlink or wrapper script for the system default CWL runner,
like `cwltool`, `toil-cwl-runner`, `arvados-cwl-runner`, etc..)

For parallel running in the style of `cwltest -j8 --test [...]` (or a fixed number of cores),
use the xdist plugin for pytest:

```
pip install pytest-xdist

pytest -n auto path/to/conformance_test_whatever.yml [...]
# auto scale the number of parallel tests

pytest -n 8 path/to/conformance_test_whatever.yml [...]
# a specific number of parallel test running

pytest -n 0 -s path/to/conformance_test_whatever.yml [...]
# "-n 0" disable forking, only one test at a time, good for debugging cwltest or the cwlest plugin to pytest
# "-s" is a shortcut for "--capture=no", also helps with debugging cwltest or the cwltest plugin to pytest
```

Timeout: `cwltest --timeout 1000` → `pytest --cwl-timeout 1000`

List tests: `cwltest -l --test path/to/conformance_test_whatever.yml` → `pytest --collect-only path/to/conformance_test_whatever.yml`

Run a specific test by name, `cwltest -s stdout_redirect_docker --test conformance_test_whatever.yml`
- `pytest conformance_test_whatever.yml::stdout_redirect_docker`
- or for multiple, use `pytest conformance_test_whatever.yml -k "stdout_redirect_docker or anonymous_enum_in_array"`

Exclude a test by name (`cwltest -S`):
`pytest conformance_test_whatever.yml -k "not anonymous_enum_in_array"`
Note that this will exclude any test that begins (or otherwise contains) the same name.

jUnit XML: `cwltest --junit-xml report.xml --test conformance_test_whatever.yml` becomes `pytest --junit-xml=report.xml conformance_test_whatever.yml`
# explain differences from cwltest

`cwltest --verbose` → `pytest -v` (print test names) or `pytest -vv` or `pytest -vvv`

Not yet supported
- `cwltest --only-tools`
- `cwltest --tags`
- `cwltest --show-tags`
- `cwltest --junit-verbose`
- `cwltest --test-arg`
- `cwltest -- args-for-runner1 args-for runner2`
- `cwltest --classname`
