# LQ-063: the tag is human-readable; the manifest-list digest is authoritative.
ARG PYTHON_IMAGE=python:3.14.7-alpine3.24@sha256:9e9fde4d32eedce0b661d9ab91e826b62dddf28e928c230ec55f1866cac66b01

FROM ${PYTHON_IMAGE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY requirements/ci.lock requirements/ci.lock
RUN python -m pip install --constraint requirements/ci.lock build==1.5.0 setuptools==80.10.2 wheel==0.47.0
COPY pyproject.toml README.md ./
COPY src/ src/
COPY tools/ tools/
ARG SOURCE_DATE_EPOCH=0
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}
RUN python -m build --wheel --no-isolation --outdir /wheelhouse

FROM ${PYTHON_IMAGE} AS runtime
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="Liquent Platform" \
      org.opencontainers.image.description="Liquent control-plane runtime" \
      org.opencontainers.image.source="https://github.com/Nexvero/liquent" \
      org.opencontainers.image.revision="${VCS_REF}"
ENV PATH=/opt/liquent/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN addgroup -g 10001 -S liquent \
    && adduser -u 10001 -S -D -H -h /nonexistent -s /sbin/nologin -G liquent liquent \
    && python -m venv /opt/liquent/venv
COPY requirements/ci.lock /tmp/ci.lock
COPY --from=builder /wheelhouse /wheelhouse
RUN python -m pip install --constraint /tmp/ci.lock /wheelhouse/liquent-*.whl \
    && python -m pip check \
    && rm -rf /wheelhouse /tmp/ci.lock \
    && mkdir -p /var/lib/liquent/artifacts \
    && chown -R liquent:liquent /var/lib/liquent
USER 10001:10001
WORKDIR /var/lib/liquent
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]
CMD ["liquent-control-plane"]
