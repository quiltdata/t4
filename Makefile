githook:
	ln -s -f ../../git_configs/hooks/pre-push .git/hooks/pre-push
	ln -s -f ../../git_configs/hooks/pre-commit .git/hooks/pre-commit

install: githook
	pip install -e ocean pip-tools
	pip-compile ocean/setup.py
	pip-sync ocean/setup.txt requirements.txt

clean:
	find . -name "*.pyc" -exec rm -f {} \;