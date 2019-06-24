TOP_DIRECTORY = '.'
TEST_DIRECTORY = 'tests'

default:
	python3 -B -m unittest discover -v -t $(TOP_DIRECTORY) -s ./$(TEST_DIRECTORY)

base:
	python3 -B -m unittest discover -v -t $(TOP_DIRECTORY) -s ./$(TEST_DIRECTORY) -p "*base*"

tic:
	python3 -B -m unittest discover -v -t $(TOP_DIRECTORY) -s ./$(TEST_DIRECTORY) -p "*tic*"

stepper:
	python3 -B -m unittest discover -v -t $(TOP_DIRECTORY) -s ./$(TEST_DIRECTORY) -p "*stepper*"

dc:
	python3 -B -m unittest discover -v -t $(TOP_DIRECTORY) -s ./$(TEST_DIRECTORY) -p "*dc*"
