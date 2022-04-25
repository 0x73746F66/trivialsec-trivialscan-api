FROM public.ecr.aws/lambda/python:3.9

LABEL org.opencontainers.image.authors="Christopher Langton"
LABEL org.opencontainers.image.version="0.0.1"
LABEL org.opencontainers.image.source="https://gitlab.com/trivialsec/trivialscan-api"

ENV PYTHONPATH ${PYTHONPATH}

COPY setup.py .
RUN echo "Installing from setup.py" \
    && python -m pip install --progress-bar off -U --no-cache-dir -e .
