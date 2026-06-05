################################################################################
# Makefile — Automated Test (n8n MCP Server)
#
# Prinsip:
#  - SEMUA test (lint + unit) berjalan DI DALAM Docker.
#  - Perintah yang sama (`make test`) dipakai di LOKAL maupun di GitHub Actions
#    → tidak mungkin ada perbedaan antara lokal dan CI.
#  - Source di-COPY ke image (bukan bind-mount), sehingga TIDAK ADA artefak test
#    (__pycache__, .pytest_cache, dll) yang tertulis ke folder project.
################################################################################

IMAGE_NAME ?= $(shell basename $(CURDIR))-test
DOCKERFILE ?= Dockerfile.test
DOCKER_RUN  = docker run --rm $(IMAGE_NAME)

.DEFAULT_GOAL := test
.PHONY: build lint unit test clean help

## help: tampilkan daftar target
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed -e 's/## //'

## build: bangun image test (deps + tooling + source)
build:
	docker build -f $(DOCKERFILE) -t $(IMAGE_NAME) .

## lint: jalankan linter di dalam container (ruff + isort + black)
lint: build
	$(DOCKER_RUN) sh -c "ruff check . && isort --check-only --diff . && black --check ."

## unit: jalankan unit test (pytest) di dalam container
unit: build
	$(DOCKER_RUN) pytest

## test: gate lengkap = lint + unit. Dipakai LOKAL dan CI (identik).
test: lint unit

## clean: hapus image test
clean:
	-docker rmi $(IMAGE_NAME)
