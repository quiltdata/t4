githook:
	ln -s -f ../../git_configs/hooks/pre-push .git/hooks/pre-push
	ln -s -f ../../git_configs/hooks/pre-commit .git/hooks/pre-commit

install: githook
	pip3 install -e sdk/python pip-tools
	pip-compile sdk/python/setup.py
	pip-sync sdk/python/setup.txt requirements.txt

clean:
	find . -name "*.pyc" -exec rm -f {} \;