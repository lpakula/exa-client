#!/usr/bin/env bash

: ${FLASK_DEBUG:=0}

FLASK_DEBUG=${FLASK_DEBUG}
FLASK_APP=__init__ flask run --host=0.0.0.0
