FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    PIP_ROOT_USER_ACTION=ignore

# Build deps for georinex (Hatanaka decompression), pyproj, scipy, ncompress
# (legacy .Z SP3 fallback used in download_inputs.py).
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        build-essential \
        ncompress \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml setup.py MANIFEST.in README.md LICENSE ./
COPY pyOASIS ./pyOASIS
COPY src ./src
COPY services ./services
COPY paper ./paper
COPY notebooks ./notebooks
COPY conftest.py download_inputs.py main.py ./

# Install both packages declared in pyproject.toml.
RUN pip install -e ".[api,paper]" tabulate

# Default working layout — can be overridden by mounted volumes.
RUN mkdir -p /data/INPUT/RINEX /data/INPUT/ORBITS /data/OUTPUT \
             /data/processed /data/training_snapshots /data/space_weather \
             /data/cache /data/models /data/labels

ENV EPB_PATH_RINEX_INPUT=/data/INPUT/RINEX \
    EPB_PATH_ORBIT_INPUT=/data/INPUT/ORBITS \
    EPB_PATH_PYOASIS_OUTPUT=/data/OUTPUT \
    EPB_PATH_DATA_RAW=/data/raw \
    EPB_PATH_DATA_PROCESSED=/data/processed \
    EPB_PATH_DATA_SNAPSHOTS=/data/training_snapshots \
    EPB_PATH_DATA_SPACE_WEATHER=/data/space_weather \
    EPB_PATH_CACHE=/data/cache \
    EPB_PATH_MODELS=/data/models

EXPOSE 8000

CMD ["python", "-m", "epb_detector.cli", "--help"]
