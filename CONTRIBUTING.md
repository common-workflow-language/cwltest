# Coding agents
For copyright and licensing reasons we can't accept any contributions made with
Claude or other LLM based coding agents. You can use whatever tools you want for
code exploration, but we can only accept human written code for the CWL project.

# Style guide
- PEP-8 / format with ``black`` via ``make format``
- Python 3.10+ compatible code
- PEP-484 type hints

In order to contribute to the development of ``cwltest``, you need to install from source (preferably in a virtual environment):
Here's a rough guide (improvements are welcome!) 
- Clone the Git repository: ``git clone https://github.com/common-workflow-language/cwltest.git``
- Switch to repository directory: ``cd cwltest``
- Create a virtual environment: ``python3 -m venv env``
- To begin using the virtual environment, it needs to be activated: ``source env/bin/activate``
- To check if you have the virtual environment set up: ``which python`` and it should point to python executable in your virtual env
- Install cwltest in the virtual environment: ``pip install -e .``
- Check the version which might be different from the version installed in general on any system: ``pip show cwltest``
- After you've made the changes, you can the complete test suite via tox: ``tox``
	- If you want to run specific tests, say ``unit tests`` in Python 3.13, then: ``tox run -e py313-unit``.
	- Look at ``tox -l`` for all available tests and runtimes
- If tests are passing, you can create a PR on the ``cwltest`` GitHub repository.
- After you're done working on with ``cwltest``, you can deactivate the virtual environment: ``deactivate``
