TARGET?=test

test:
	PYTHONPATH="." python -m pytest tests/ --junit-xml testresults.xml -rxsw -v

compile:
	@echo Compiling python code
	python -m compileall peix

compile_optimized:
	@echo Compiling python code optimized
	python -O -m compileall peix

coverage:
	coverage erase
	PYTHONPATH="." coverage run --source='peix' --branch -m py.test -qq tests/
	coverage xml -i
	coverage report -m

clean:
	find -name "*.py?" -delete
	rm -f coverage.xml
	rm -f testresults.xml
	rm -fr htmlcov dist *.egg-info

travis: compile compile_optimized test coverage

install_deps:
	pip install -r requirements.txt
	pip install -r requirements_dev.txt

jenkins: install_deps travis

