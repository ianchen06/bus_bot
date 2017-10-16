#!/bin/sh
gunicorn app:app \
    --workers 2 \
    --bind unix:/tmp/gunicorn.sock \
    --log-file ./gunicorn.log \
    --log-level DEBUG \
    --reload
