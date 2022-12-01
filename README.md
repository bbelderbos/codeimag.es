# Pybites Code Images API

An API to create code images using [pybites-carbon](https://github.com/PyBites-Open-Source/pybites-carbon), upload them to an S3 bucket and host them in a central database.

This app currently runs on Heroku [here](http://pybites-codeimages.herokuapp.com):

<img width="1515" alt="codeimages-website" src="https://user-images.githubusercontent.com/387927/205053842-a78ca55c-4c1a-4167-a4a1-45cc865a5064.png">

The API supports signup with email verification. 

This repo also includes a script to [authenticate and post tips to the API](https://github.com/bbelderbos/codeimag.es/blob/main/tips/post_snippet.py).

## Setup

To run it locally create a virtual environment and install the dependencies

```
$ python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
# or
$ make setup
```

Then run the server with:

```
$ uvicorn tips.main:app --reload
# or
$ make runserver
```

... and navigate to `http://localhost:8000/docs`


## Dev tooling

For linting, type checking and pytest / coverage you can run the following commands:

```
$ make lint
$ make typing
$ make cov
```

## Contributing

Any help to make this tool better is welcome, please log an issue [here](https://github.com/bbelderbos/codeimag.es/issues) (for pybites-carbon related issues, use its repo [here](https://github.com/PyBites-Open-Source/pybites-carbon)) - thanks.
