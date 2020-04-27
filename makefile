unit-test:
	python -m src.overseer-test

run:
	sudo python src/overseer

deploy:
	scp src/overseer.py meowxiik@nuc:/home/meowxiik
	ssh meowxiik@nuc -tt 'sudo cp /home/meowxiik/overseer.py /usr/local/bin/overseer'
	ssh meowxiik@nuc 'rm /home/meowxiik/overseer.py'

deploy-run:
	scp src/overseer.py meowxiik@nuc:/home/meowxiik
	ssh meowxiik@nuc -tt 'sudo cp /home/meowxiik/overseer.py /usr/local/bin/overseer'
	ssh meowxiik@nuc 'rm /home/meowxiik/overseer.py'
	ssh meowxiik@nuc -tt 'sudo overseer -v'

deploy-debug:
	scp src/overseer.py meowxiik@nuc:/home/meowxiik	
	ssh meowxiik@nuc -tt 'sudo cp /home/meowxiik/overseer.py /usr/local/bin/overseer'
	ssh meowxiik@nuc 'rm /home/meowxiik/overseer.py'
	ssh meowxiik@nuc -tt 'sudo pudb3 /usr/local/bin/overseer'
