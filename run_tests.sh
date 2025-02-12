#!/bin/bash

echo "Running tests with coverage..."

# Run tests with coverage
coverage run -m unittest discover tests

# Show coverage summary in the terminal
coverage report -m

# Generate a detailed HTML report
coverage html

echo "Code coverage report generated in htmlcov/index.html"
