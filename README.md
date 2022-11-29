# Pybites code images API

An API to create code images using [pybites-carbon](https://github.com/PyBites-Open-Source/pybites-carbon) and upload them to an S3 bucket.

## Setup

Create a virtual environment and install the dependencies

```
$ python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
# or
$ make setup
```

Then run the server with:

```
uvicorn tips.main:app --reload
# or
$ make runserver
```

... and navigate to `http://localhost:8000/docs`

This app currently runs on Heroku [here](http://pybites-codeimages.herokuapp.com).

## Dev tooling

For linting, type checking and pytest / coverage you can run the following commands:

```
$ make lint
$ make typing
$ make cov
```

## Contributing

Any help to make this tool better is welcome, please log an issue [here](https://github.com/bbelderbos/codeimag.es/issues) (for pybites-carbon related issues, use [its repo](https://github.com/PyBites-Open-Source/pybites-carbon)) - thanks.
