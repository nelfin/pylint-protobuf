.PHONY: dist test clean upload
dist: test
	python setup.py sdist bdist_wheel

test:
	tox

clean:
	-rm -r dist/

upload: clean dist
	twine upload dist/*
