""" Discovers CWL test files and converts them to pytest.Items """
import pytest
from cwltest import run_test_plain, DEFAULT_TIMEOUT

def pytest_collect_file(parent, path):
    """Is this file for us?"""
    if (path.ext == ".yml" or path.ext == ".yaml") \
            and path.basename.startswith("conformance_test"):
        return YamlFile(path, parent)
    return None

class YamlFile(pytest.File):
    """A CWL test file."""
    def collect(self):
        import yaml  # we need a yaml parser, e.g. PyYAML
        raw = yaml.safe_load(self.fspath.open())
        for entry in raw:
            name = entry["short_name"] if "short_name" in entry \
                else entry["doc"]
            yield CWLItem(name, self, entry)

class CWLItem(pytest.Item):
    """A CWL test Item."""
    def __init__(self, name, parent, spec):
        super(CWLItem, self).__init__(name, parent)
        self.spec = spec

    def runtest(self):
        """Execute using cwltest"""
        args = {'tool': 'cwltool',
                'args': {'--enable-dev'},
                'testargs': None,
                'verbose': True,
                'classname': 'cwltool'}
        result = run_test_plain(args, self.spec, DEFAULT_TIMEOUT)

        if result.return_code != 0:
            raise CWLTestException(self, result)

    def repr_failure(self, excinfo):
        """ called when self.runtest() raises an exception. """
        if isinstance(excinfo.value, CWLTestException):
            import yaml
            result = excinfo.value.args[1]
            return "\n".join([
                "CWL test execution failed. ",
                "{}".format(result.message),
                "Test: {}".format(yaml.dump(self.spec))
            ])
        return None

    def reportinfo(self):
        return self.fspath, 0, "cwl test: %s" % self.name

class CWLTestException(Exception):
    """ custom exception for error reporting. """
