ROOT=$(realpath $(dir $(lastword $(MAKEFILE_LIST))))
REPETITIONS=5
ARCH=$(shell uname -m)
LLVM_DIR=$(ROOT)/llvm
TPDE_DIR=$(ROOT)/tpde
TPDE_OLD_DIR=$(ROOT)/tpde-old

# Prevent cleanup of stamp files. .NOTINTERMEDIATE is buggy on older make.
.SECONDARY:

RESULTS= latex/bench-res/res-spec-ct-$(ARCH) latex/bench-res/res-spec-rt-$(ARCH)

.PHONY: all all-x86_64 all-aarch64 all-spec
all: latex/bench-res/res-test-suite-ct-$(ARCH) latex/bench-res/res-test-suite-rt-text-$(ARCH) latex/figures_$(ARCH).pdf all-$(ARCH)

all-x86_64: 

all-aarch64:

all-spec: all res-spec-ct res-spec-rt latex/figures_spec_$(ARCH).pdf

DATABASES=db/tpcdsSf1.db db/tpcdsSf10.db

.PHONY: prepare
prepare: $(DATABASES)

.PHONY: clean
clean:
	rm -rf tpcds-kit tpcds-data db latex/bench-res/res-*
	# if the config files do not exists, this command errors
	-$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-ct --action trash intspeed
	-$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-clang-ct --action trash intspeed
	-$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-rt --expid=paper-tpde-rt --action trash intspeed
	-$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-clang-rt --expid=paper-clang-rt --action trash intspeed
	rm -rf spec/result/
	rm -rf $(ROOT)/testsuite/llvm-test-suite/build_llvm_O0
	rm -rf $(ROOT)/testsuite/llvm-test-suite/build_llvm_O1
	rm -rf $(ROOT)/testsuite/llvm-test-suite/build_tpde
	rm -rf $(ROOT)/testsuite/llvm-test-suite/build_tpde_old
	mkdir spec/result


ifeq ($(ARCH), aarch64)
EXTRA_FLAGS="-Xclang -mlong-double-64"
else
EXTRA_FLAGS="-mlong-double-64"
endif

testsuite/llvm-test-suite/build_%:
	cd testsuite/llvm-test-suite; cmake -B build_$* -DCMAKE_BUILD_TYPE=Debug -G Ninja -DLIT=lit -DCMAKE_CXX_COMPILER=$(LLVM_DIR)/bin/clang++ -DCMAKE_C_COMPILER=$(LLVM_DIR)/bin/clang -DCMAKE_C_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DCMAKE_CXX_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DLLVM_DIR=$(LLVM_DIR)/lib64/cmake -DTEST_SUITE_BENCHMARKING_ONLY=ON -DTEST_SUITE_RUN_BENCHMARKS=1 -DTEST_SUITE_COLLECT_CODE_SIZE=ON -Ccmake/caches/O2.cmake -DTEST_SUITE_COLLECT_STATS=OFF -DTEST_SUITE_COLLECT_COMPILE_TIME=OFF -DTEST_SUITE_SUBDIRS="MultiSource" -DCMAKE_C_FLAGS=$(EXTRA_FLAGS) -DCMAKE_CXX_FLAGS=$(EXTRA_FLAGS)

latex/bench-res:
	mkdir latex/bench-res

latex/bench-res/res-test-suite-ct-$(ARCH): | testsuite/llvm-test-suite/build_llvm_O0 testsuite/llvm-test-suite/build_llvm_O1 testsuite/llvm-test-suite/build_tpde testsuite/llvm-test-suite/build_tpde_old latex/bench-res 
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O0" ninja -C build_llvm_O0 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O1" ninja -C build_llvm_O1 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_DIR)/tpde-llvm/tpde-llc" ninja -C build_tpde -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_OLD_DIR)/tpde-llvm/tpde-llc" ninja -C build_tpde_old -j 4
	cd testsuite/llvm-test-suite; ../parse_traces.sh | tee $(ROOT)/$@

latex/bench-res/res-test-suite-rt-text-$(ARCH): latex/bench-res/res-test-suite-ct-$(ARCH)
	cd testsuite/llvm-test-suite; ../run_benches.sh | tee $(ROOT)/$@

latex/figures_$(ARCH).pdf:: latex/bench-res/res-total-tpcdsSf1-$(ARCH) latex/bench-res/res-test-suite-ct-$(ARCH) latex/bench-res/res-test-suite-rt-text-$(ARCH)
	cd latex && make all