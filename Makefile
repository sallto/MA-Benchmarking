DOCKER_TOOL?=docker
ROOT=$(realpath $(dir $(lastword $(MAKEFILE_LIST))))
ARCH=$(shell uname -m)
SHELL := /bin/bash

.PHONY: clean prepare all all-spec prepare_uber uber-cli

clean:
	-[ -f container_id.txt ] && $(DOCKER_TOOL) rm `cat container_id.txt`
	-[ -f container_id_uber.txt ] && $(DOCKER_TOOL) rm `cat container_id_uber.txt`
	-$(DOCKER_TOOL) rmi tpde-cgo-bench-$(ARCH)
	-$(DOCKER_TOOL) rmi tpde-cgo-uber-$(ARCH)
	-rm -f container_id.txt
	-rm -f container_id_uber.txt

container_id.txt:
	$(DOCKER_TOOL) image load --input $(ROOT)/images/tpde-cgo-bench-$(ARCH).tar.gz 
ifneq ($(SPEC_INSTALL_DIR),)
	$(DOCKER_TOOL) create -it --name tpde_cgo ${DOCKER_CPUSET:+--cpuset-cpus "$DOCKER_CPUSET"} -v $(SPEC_INSTALL_DIR):/spec_mount:ro,Z localhost/tpde-cgo-bench-$(ARCH) > $@
else
	$(DOCKER_TOOL) create -it --name tpde_cgo ${DOCKER_CPUSET:+--cpuset-cpus "$DOCKER_CPUSET"} localhost/tpde-cgo-bench-$(ARCH) > $@
endif

container_id_uber.txt:
	$(DOCKER_TOOL) image load --input $(ROOT)/images/tpde-cgo-uber-$(ARCH).tar.gz
ifneq ($(SPEC_INSTALL_DIR),)
	$(DOCKER_TOOL) create -it --name tpde_cgo_uber ${DOCKER_CPUSET:+--cpuset-cpus "$DOCKER_CPUSET"} -v $(SPEC_INSTALL_DIR):/spec_mount:ro,Z localhost/tpde-cgo-uber-$(ARCH) > $@
else
	$(DOCKER_TOOL) create -it --name tpde_cgo_uber ${DOCKER_CPUSET:+--cpuset-cpus "$DOCKER_CPUSET"} localhost/tpde-cgo-uber-$(ARCH) > $@
endif

prepare: container_id.txt
ifneq ($(SPEC_INSTALL_DIR),)
	$(DOCKER_TOOL) start -ai `cat container_id.txt` <<< "make spec; exit;"
endif

prepare_uber: container_id_uber.txt
ifneq ($(SPEC_INSTALL_DIR),)
	$(DOCKER_TOOL) start -ai `cat container_id_uber.txt` <<< "make spec; exit;"
endif

all: container_id.txt prepare
	$(DOCKER_TOOL) start -ai `cat container_id.txt` <<< "make all; exit;"
	$(DOCKER_TOOL) cp `cat container_id.txt`:/bench/latex ./latex.`cat container_id.txt`

all-spec: container_id.txt prepare
	$(DOCKER_TOOL) start -ai `cat container_id.txt` <<< "make all-spec; exit;"
	$(DOCKER_TOOL) cp `cat container_id.txt`:/bench/latex ./latex.`cat container_id.txt`


uber-cli:
	$(DOCKER_TOOL) start -ai `cat container_id_uber.txt`
