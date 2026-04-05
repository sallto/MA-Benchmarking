ROOT=$(realpath $(dir $(lastword $(MAKEFILE_LIST))))
ARCH=$(shell uname -m)
LLVM_DIR=$(ROOT)/llvm
TPDE_DIR=$(ROOT)/tpde
TPDE_OLD_DIR=$(ROOT)/tpde-old

# Prevent cleanup of stamp files. .NOTINTERMEDIATE is buggy on older make.
.SECONDARY:

RESULTS= latex/bench-res/res-spec-ct-$(ARCH) latex/bench-res/res-spec-rt-$(ARCH)

.PHONY: all
all: res-spec-rt bench-res-rt 
all-x86_64: 

all-aarch64:

all-spec: all res-spec-ct res-spec-rt latex/figures_spec_$(ARCH).pdf


.PHONY: clean
clean:
	rm -rf latex/bench-res/res-*
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



# Install SPEC
spec:
	/spec_mount/install.sh -f -d /bench/spec


spec/config/$(ARCH)-%-ct.cfg: spec_config/$(ARCH)-%-ct.cfg spec_config/$(ARCH)-base.cfg | spec
	cp spec_config/$(ARCH)-$*-ct.cfg spec/config/$(ARCH)-$*-ct.cfg
	echo "%define gcc_dir \"$(LLVM_DIR)\"" >> spec/config/$(ARCH)-$*-ct.cfg
	echo "%define artifact_dir \"$(ROOT)\"" >> spec/config/$(ARCH)-$*-ct.cfg
	cat spec_config/$(ARCH)-base.cfg >> spec/config/$(ARCH)-$*-ct.cfg

spec/config/$(ARCH)-%-rt.cfg: spec_config/$(ARCH)-%-rt.cfg spec_config/$(ARCH)-base.cfg | spec
	cp spec_config/$(ARCH)-$*-rt.cfg spec/config/$(ARCH)-$*-rt.cfg
	echo "%define gcc_dir \"$(LLVM_DIR)\"" >> spec/config/$(ARCH)-$*-rt.cfg
	echo "%define artifact_dir \"$(ROOT)\"" >> spec/config/$(ARCH)-$*-rt.cfg
	cat spec_config/$(ARCH)-base.cfg >> spec/config/$(ARCH)-$*-rt.cfg

latex/bench-res/res-spec-raw-ct-$(ARCH): spec/config/$(ARCH)-clang-ct.cfg spec/config/$(ARCH)-tpde-ct.cfg spec/config/$(ARCH)-tpde-old-ct.cfg | spec latex/bench-res 
	# create build directories
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-clang-ct.cfg  --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-ct.cfg --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-old-ct.cfg --action=buildsetup intspeed
	-rm latex/bench-res/res-spec-raw-ct-$(ARCH)
	$(ROOT)/run_ct_bench.sh "$(ROOT)/spec" $(ARCH) latex/bench-res/res-spec-raw-ct-$(ARCH) true -O0

latex/bench-res/res-spec-raw-ct-o1ir-$(ARCH): spec/config/$(ARCH)-clang-ct.cfg spec/config/$(ARCH)-tpde-ct.cfg spec/config/$(ARCH)-tpde-old-ct.cfg | spec latex/bench-res 
	# create build directories
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-clang-ct.cfg --define o1ir --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-ct.cfg --define o1ir --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-old-ct.cfg --define o1ir --action=buildsetup intspeed
	-rm latex/bench-res/res-spec-raw-ct-o1ir-$(ARCH)
	$(ROOT)/run_ct_bench.sh "$(ROOT)/spec" $(ARCH) latex/bench-res/res-spec-raw-ct-o1ir-$(ARCH) true -O0

latex/bench-res/res-spec-raw-ct-o1-$(ARCH): spec/config/$(ARCH)-clang-ct.cfg spec/config/$(ARCH)-tpde-ct.cfg spec/config/$(ARCH)-tpde-old-ct.cfg | spec latex/bench-res 
	# create build directories
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-clang-ct.cfg --define o1ir --define o1llc --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-ct.cfg --define o1ir --define o1llc --action=buildsetup intspeed
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-tpde-old-ct.cfg --define o1ir --define o1llc --action=buildsetup intspeed
	-rm latex/bench-res/res-spec-raw-ct-o1-$(ARCH)
	$(ROOT)/run_ct_bench.sh "$(ROOT)/spec" $(ARCH) latex/bench-res/res-spec-raw-ct-o1-$(ARCH) true -O1

latex/bench-res/res-spec-raw-rt-$(ARCH)-%: spec/config/$(ARCH)-%-rt.cfg | spec latex/bench-res 
	-rm -rf $(ROOT)/spec/result/paper-$*-rt
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-$*-rt.cfg -n 2 --expid=paper-$*-rt --rebuild intspeed
	# the result files are named CPU2017.001.intspeed.*
	sed -ne '/^"Selected Results Table"/{:a' -e 'n;p;ba' -e '}' $(ROOT)/spec/result/paper-$*-rt/CPU2017.001.intspeed.refspeed.csv | awk -F, '/^Benchmark/ { in_table=1 } /^$$/{ in_table=0 } in_table && $$1 ~ /^[0-9]+\..+$$/ { print substr($$1, 1, 3) ": " $$3 }' > latex/bench-res/res-spec-raw-rt-$(ARCH)-$*


latex/bench-res/res-spec-raw-rt-o1ir-$(ARCH)-%: spec/config/$(ARCH)-%-rt.cfg | spec latex/bench-res 
	-rm -rf $(ROOT)/spec/result/paper-$*-rt-o1ir
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-$*-rt.cfg --define o1ir -n 2 --expid=paper-$*-rt-o1ir --rebuild intspeed
	# the result files are named CPU2017.001.intspeed.*
	sed -ne '/^"Selected Results Table"/{:a' -e 'n;p;ba' -e '}' $(ROOT)/spec/result/paper-$*-rt-o1ir/CPU2017.001.intspeed.refspeed.csv | awk -F, '/^Benchmark/ { in_table=1 } /^$$/{ in_table=0 } in_table && $$1 ~ /^[0-9]+\..+$$/ { print substr($$1, 1, 3) ": " $$3 }' > latex/bench-res/res-spec-raw-rt-o1ir-$(ARCH)-$*

latex/bench-res/res-spec-raw-rt-o1-$(ARCH)-%: spec/config/$(ARCH)-%-rt.cfg | spec latex/bench-res 
	-rm -rf $(ROOT)/spec/result/paper-$*-rt-o1
	$(ROOT)/spec_cmd.sh runcpu --config=$(ARCH)-$*-rt.cfg --define o1ir --define o1llc -n 2 --expid=paper-$*-rt-o1 --rebuild intspeed
	# the result files are named CPU2017.001.intspeed.*
	sed -ne '/^"Selected Results Table"/{:a' -e 'n;p;ba' -e '}' $(ROOT)/spec/result/paper-$*-rt-o1/CPU2017.001.intspeed.refspeed.csv | awk -F, '/^Benchmark/ { in_table=1 } /^$$/{ in_table=0 } in_table && $$1 ~ /^[0-9]+\..+$$/ { print substr($$1, 1, 3) ": " $$3 }' > latex/bench-res/res-spec-raw-rt-o1-$(ARCH)-$*


.PHONY: res-spec-raw-rt-o1ir-$(ARCH)
res-spec-raw-rt-o1ir-$(ARCH): latex/bench-res/res-spec-raw-rt-o1ir-$(ARCH)-tpde latex/bench-res/res-spec-raw-rt-o1ir-$(ARCH)-clang  latex/bench-res/res-spec-raw-rt-o1ir-$(ARCH)-tpde-old

.PHONY: res-spec-raw-rt-o1-$(ARCH)
res-spec-raw-rt-o1-$(ARCH): latex/bench-res/res-spec-raw-rt-o1-$(ARCH)-clang

.PHONY: res-spec-ct
res-spec-ct: latex/bench-res/res-spec-raw-ct-o1-$(ARCH) latex/bench-res/res-spec-raw-ct-o1ir-$(ARCH) latex/bench-res/res-spec-raw-ct-$(ARCH)

.PHONY: res-spec-rt
res-spec-rt: res-spec-raw-rt-o1ir-$(ARCH) res-spec-raw-rt-o1-$(ARCH) res-spec-raw-rt-$(ARCH) latex/bench-res/res-spec-raw-ct-o1-$(ARCH) latex/bench-res/res-spec-raw-ct-o1ir-$(ARCH) latex/bench-res/res-spec-raw-ct-$(ARCH)

ifeq ($(ARCH), aarch64)
EXTRA_FLAGS="-Xclang -mlong-double-64 -g"
else
EXTRA_FLAGS="-mlong-double-64 -g"
endif

testsuite/llvm-test-suite/build_%:
	cd testsuite/llvm-test-suite; cmake -B build_$* -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS_RELEASE="-O1 -g" -DCMAKE_CXX_FLAGS_RELEASE="-O1 -g" -G Ninja -DLIT=lit -DCMAKE_CXX_COMPILER=$(LLVM_DIR)/bin/clang++ -DCMAKE_C_COMPILER=$(LLVM_DIR)/bin/clang -DCMAKE_C_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DCMAKE_CXX_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DLLVM_DIR=$(LLVM_DIR)/lib64/cmake -DTEST_SUITE_BENCHMARKING_ONLY=ON -DTEST_SUITE_RUN_BENCHMARKS=1 -DTEST_SUITE_COLLECT_CODE_SIZE=ON -DTEST_SUITE_COLLECT_STATS=OFF -DTEST_SUITE_COLLECT_COMPILE_TIME=OFF -DTEST_SUITE_SUBDIRS="MultiSource" -DCMAKE_C_FLAGS=$(EXTRA_FLAGS) -DCMAKE_CXX_FLAGS=$(EXTRA_FLAGS)


testsuite/llvm-test-suite/O0_build_%:
	cd testsuite/llvm-test-suite; cmake -B O0_build_$* -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS_RELEASE="-O0 -g" -DCMAKE_CXX_FLAGS_RELEASE="-O0 -g" -G Ninja -DLIT=lit -DCMAKE_CXX_COMPILER=$(LLVM_DIR)/bin/clang++ -DCMAKE_C_COMPILER=$(LLVM_DIR)/bin/clang -DCMAKE_C_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DCMAKE_CXX_COMPILER_LAUNCHER=$(ROOT)/testsuite/tpde-clang -DLLVM_DIR=$(LLVM_DIR)/lib64/cmake -DTEST_SUITE_BENCHMARKING_ONLY=ON -DTEST_SUITE_RUN_BENCHMARKS=1 -DTEST_SUITE_COLLECT_CODE_SIZE=ON -DTEST_SUITE_COLLECT_STATS=OFF -DTEST_SUITE_COLLECT_COMPILE_TIME=OFF -DTEST_SUITE_SUBDIRS="MultiSource" -DCMAKE_C_FLAGS=$(EXTRA_FLAGS) -DCMAKE_CXX_FLAGS=$(EXTRA_FLAGS)


latex/bench-res:
	mkdir latex/bench-res

latex/bench-res/res-test-suite-ct-O0-$(ARCH): | testsuite/llvm-test-suite/O0_build_tpde testsuite/llvm-test-suite/O0_build_llvm_O0 testsuite/llvm-test-suite/O0_build_llvm_O1 testsuite/llvm-test-suite/O0_build_tpde-old
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_DIR)/tpde-llvm/tpde-llc" ninja -C O0_build_tpde -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O0" ninja -C O0_build_llvm_O0 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O1" ninja -C O0_build_llvm_O1 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_OLD_DIR)/tpde-llvm/tpde-llc" ninja -C O0_build_tpde-old -j 4
	cd testsuite/llvm-test-suite; ../parse_traces.sh | tee $(ROOT)/$@

latex/bench-res/res-test-suite-ct-$(ARCH): | testsuite/llvm-test-suite/build_llvm_O0 testsuite/llvm-test-suite/build_llvm_O1 testsuite/llvm-test-suite/build_tpde testsuite/llvm-test-suite/build_tpde_old latex/bench-res 
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_DIR)/tpde-llvm/tpde-llc" ninja -C build_tpde -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O0" ninja -C build_llvm_O0 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(LLVM_DIR)/bin/llc --filetype=obj --relocation-model=pic -O1" ninja -C build_llvm_O1 -j 4
	cd testsuite/llvm-test-suite; env TPDE_LLC="$(TPDE_OLD_DIR)/tpde-llvm/tpde-llc" ninja -C build_tpde_old -j 4
	cd testsuite/llvm-test-suite; ../parse_traces.sh | tee $(ROOT)/$@

latex/bench-res/res-test-suite-rt-text-$(ARCH): latex/bench-res/res-test-suite-ct-$(ARCH)
	cd testsuite/llvm-test-suite; ../run_benches.sh | tee $(ROOT)/$@

latex/bench-res/res-test-suite-rt-text-O0-$(ARCH): latex/bench-res/res-test-suite-ct-O0-$(ARCH)
	cd testsuite/llvm-test-suite; ../run_benches_O0.sh | tee $(ROOT)/$@

.PHONY: bench-res-rt
bench-res-rt: latex/bench-res/res-test-suite-rt-text-$(ARCH) latex/bench-res/res-test-suite-rt-text-O0-$(ARCH)

latex/figures_$(ARCH).pdf:: latex/bench-res/res-total-tpcdsSf1-$(ARCH) latex/bench-res/res-test-suite-ct-$(ARCH) latex/bench-res/res-test-suite-rt-text-$(ARCH)
	cd latex && make all
