githook:
	ln -s -f ../../git_configs/hooks/pre-push .git/hooks/pre-push
	ln -s -f ../../git_configs/hooks/pre-commit .git/hooks/pre-commit

install: githook
	pip3 install -e api/python pip-tools
	pip-compile api/python/setup.py
	pip-sync api/python/setup.txt requirements.txt

clean:
	find . -name "*.pyc" -exec rm -f {} \;