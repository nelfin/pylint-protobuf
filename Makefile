.PHONY: dist test coverage clean upload
dist: test
	python setup.py sdist bdist_wheel

test:
	tox

coverage:
	py.test --cov=pylint_protobuf --cov-branch
	coverage html

clean:
	-rm -r dist/

upload: clean dist
	twine check dist/*
	twine upload dist/*
