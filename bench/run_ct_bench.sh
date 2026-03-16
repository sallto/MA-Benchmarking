#!/bin/bash

set -E

# https://stackoverflow.com/a/246128
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ "$#" -ne 5 ]]; then
    echo "Usage: run_ct_bench.sh <spec_dir> <arch:x86_64/aarch64> <out_file> <llc_mode> <llc_opt_mode>"
    exit 1
fi

SPEC_DIR=$(realpath -s "$1")
ARCH="$2"
OUT_FILE="$3"
LLC_MODE="$4"
LLC_OPT_MODE="$5"

if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
    echo "Architecture must be one of 'x64' or 'aarch64'"
    exit 1
fi

echo "Script: ${SCRIPT_DIR}"
echo "SPEC: ${SPEC_DIR}"

CLANG_CFG_PATH="${SPEC_DIR}/config/${ARCH}-clang-ct.cfg"
TPDE_CFG_PATH="${SPEC_DIR}/config/${ARCH}-tpde-ct.cfg"
TPDE_OLD_CFG_PATH="${SPEC_DIR}/config/${ARCH}-tpde-old-ct.cfg"

BENCH_NUMBERS=("600" "602" "605" "620" "623" "625" "631" "641" "648" "657")
BENCH_NAMES=("perlbench" "gcc" "mcf" "omnetpp" "xalancbmk" "x264" "deepsjeng" "leela" "exchange2" "xz")

RUN_COUNT=3

rm -f "${SCRIPT_DIR}/$OUT_FILE"

for idx in ${!BENCH_NUMBERS[@]}; do
    echo "Testing ${BENCH_NUMBERS[$idx]}.${BENCH_NAMES[$idx]}"
    LIST_PATH="${SPEC_DIR}/benchspec/CPU/${BENCH_NUMBERS[$idx]}.${BENCH_NAMES[$idx]}_s/build/list"
    CLANG_BUILD_DIR=$(grep "label=${ARCH}-clang-ct" ${LIST_PATH} | grep "lock=0" | awk -F 'dir=' '{print $2}' | cut -d' ' -f1 | tail -1)
    TPDE_BUILD_DIR=$(grep "label=${ARCH}-tpde-ct" ${LIST_PATH} | grep "lock=0" | awk -F 'dir=' '{print $2}' | cut -d' ' -f1 | tail -1)
    TPDE_OLD_BUILD_DIR=$(grep "label=${ARCH}-tpde-old-ct" ${LIST_PATH} | grep "lock=0" | awk -F 'dir=' '{print $2}' | cut -d' ' -f1 | tail -1)

    echo "CLANG_BUILD_DIR: ${CLANG_BUILD_DIR}"
    echo "TPDE_BUILD_DIR: ${TPDE_BUILD_DIR}"
    echo "TPDE_OLD_BUILD_DIR: ${TPDE_OLD_BUILD_DIR}"

    NAME_ARR=("clang" "tpde" "tpde_old ")
    BUILD_DIRS=("${CLANG_BUILD_DIR}" "${TPDE_BUILD_DIR}" "${TPDE_OLD_BUILD_DIR}")
	LLCS=("${SCRIPT_DIR}/llvm/bin/llc --filetype=obj --relocation-model=pic ${LLC_OPT_MODE}" "${SCRIPT_DIR}/tpde/tpde-llvm/tpde-llc" "${SCRIPT_DIR}/tpde-old/tpde-llvm/tpde-llc")

    rm -rf ${CLANG_BUILD_DIR}/time_trace*
    rm -rf ${TPDE_BUILD_DIR}/time_trace*
    rm -rf ${TPDE_OLD_BUILD_DIR}/time_trace*

    if [ "${BENCH_NUMBERS[$idx]}" == "625" ]; then
        # x264 needs special handling since it has multiple targets...

	for ty_idx in ${!NAME_ARR[@]}; do
	    (cd "${SPEC_DIR}" && source shrc && cd "${BUILD_DIRS[$ty_idx]}" && {
		for i in $(seq 1 $RUN_COUNT); do
                    echo "Run ${i} for ${NAME_ARR[$ty_idx]} [$(date "+%F %H:%M:%S")]"
                    
	     	mkdir "time_trace.${i}"
		rm -f make.out
	    	
	    	for target in "ldecod_s" "imagevalidate_625" "x264_s"; do
                        rm -rf time_trace
                        mkdir time_trace
			export TPDE_LLC="${LLCS[$ty_idx]}"
                        make clean TARGET=${target} >/dev/null && taskset -c 4-7 make TARGET=${target} -j4 1>/dev/null 2>>make.out
                        mv time_trace "time_trace.${i}/${target}"
	    	done
                done
            })
        done
    else
	for ty_idx in ${!NAME_ARR[@]}; do
            (cd "${SPEC_DIR}" && source shrc && cd "${BUILD_DIRS[$ty_idx]}" && {
		    for i in $(seq 1 $RUN_COUNT); do
                    echo "Run ${i} for ${NAME_ARR[$ty_idx]} [$(date "+%F %H:%M:%S")]"
                    rm -rf time_trace
                    mkdir time_trace
					export TPDE_LLC="${LLCS[$ty_idx]}"
                    make clean >/dev/null && taskset -c 4-7 make -j4 1>/dev/null 2>make.out
                    mv time_trace "time_trace.${i}"
                done
            })
        done
    fi
 
    echo "${BENCH_NUMBERS[$idx]}:" >> "${SCRIPT_DIR}/${OUT_FILE}"
    if [ "${BENCH_NUMBERS[$idx]}" == "648" ]; then
        # exchange2 always needs LLC mode
        python3 "${SCRIPT_DIR}/parse_trace_jsons.py" "${BENCH_NUMBERS[$idx]}" "${CLANG_BUILD_DIR}" "${TPDE_BUILD_DIR}" "${TPDE_OLD_BUILD_DIR}" "true" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
    else
        python3 "${SCRIPT_DIR}/parse_trace_jsons.py" "${BENCH_NUMBERS[$idx]}" "${CLANG_BUILD_DIR}" "${TPDE_BUILD_DIR}" "${TPDE_OLD_BUILD_DIR}" "${LLC_MODE}" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
    fi

    if [ "${BENCH_NUMBERS[$idx]}" == "625" ]; then
        # x264 needs special handling since it has multiple targets...
        TEXT_SIZE_CLANG1=$(size -A -d "${CLANG_BUILD_DIR}/ldecod_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_CLANG2=$(size -A -d "${CLANG_BUILD_DIR}/imagevalidate_625" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_CLANG3=$(size -A -d "${CLANG_BUILD_DIR}/x264_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE1=$(size -A -d "${TPDE_BUILD_DIR}/ldecod_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE2=$(size -A -d "${TPDE_BUILD_DIR}/imagevalidate_625" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE3=$(size -A -d "${TPDE_BUILD_DIR}/x264_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD1=$(size -A -d "${TPDE_OLD_BUILD_DIR}/ldecod_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD2=$(size -A -d "${TPDE_OLD_BUILD_DIR}/imagevalidate_625" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD3=$(size -A -d "${TPDE_OLD_BUILD_DIR}/x264_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_CLANG=$TEXT_SIZE_CLANG1+$TEXT_SIZE_CLANG2+$TEXT_SIZE_CLANG3
        TEXT_SIZE_TPDE=$TEXT_SIZE_TPDE1+$TEXT_SIZE_TPDE2+$TEXT_SIZE_TPDE3
        TEXT_SIZE_TPDE_OLD=$TEXT_SIZE_TPDE_OLD1+$TEXT_SIZE_TPDE_OLD2+$TEXT_SIZE_TPDE_OLD3
	TEXT_RATIO=$(awk "BEGIN{printf \"%.2f\n\",(${TEXT_SIZE_TPDE})/(${TEXT_SIZE_TPDE_OLD})}")
        echo "${BENCH_NUMBERS[$idx]} text clang: $TEXT_SIZE_CLANG" >> "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde: $TEXT_SIZE_TPDE" >> "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde-old: $TEXT_SIZE_TPDE_OLD" >> "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text ratio: $TEXT_RATIO" >> "${SCRIPT_DIR}/${OUT_FILE}"
    elif [ "${BENCH_NUMBERS[$idx]}" == "648" ]; then
	# Use object file; Flang links statically against the runtime, which we don't want to include
        TEXT_SIZE_CLANG=$(size -A -d "${CLANG_BUILD_DIR}/exchange2.fppized.o" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE=$(size -A -d "${TPDE_BUILD_DIR}/exchange2.fppized.o" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD=$(size -A -d "${TPDE_OLD_BUILD_DIR}/exchange2.fppized.o" | grep ".text" | awk '{print $2}')
        TEXT_RATIO=$(awk "BEGIN{printf \"%.2f\n\",${TEXT_SIZE_TPDE}/${TEXT_SIZE_TPDE_OLD}}")
        echo "${BENCH_NUMBERS[$idx]} text clang: $TEXT_SIZE_CLANG" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde: $TEXT_SIZE_TPDE" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde-old: $TEXT_SIZE_TPDE_OLD" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text ratio: $TEXT_RATIO" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
    elif [ "${BENCH_NUMBERS[$idx]}" == "602" ]; then
        TEXT_SIZE_CLANG=$(size -A -d "${CLANG_BUILD_DIR}/sgcc" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE=$(size -A -d "${TPDE_BUILD_DIR}/sgcc" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD=$(size -A -d "${TPDE_OLD_BUILD_DIR}/sgcc" | grep ".text" | awk '{print $2}')
        TEXT_RATIO=$(awk "BEGIN{printf \"%.2f\n\",${TEXT_SIZE_TPDE}/${TEXT_SIZE_TPDE_OLD}}")
        echo "${BENCH_NUMBERS[$idx]} text clang: $TEXT_SIZE_CLANG" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde: $TEXT_SIZE_TPDE" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde-old: $TEXT_SIZE_TPDE_OLD" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text ratio: $TEXT_RATIO" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
    else
        TEXT_SIZE_CLANG=$(size -A -d "${CLANG_BUILD_DIR}/${BENCH_NAMES[$idx]}_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE=$(size -A -d "${TPDE_BUILD_DIR}/${BENCH_NAMES[$idx]}_s" | grep ".text" | awk '{print $2}')
        TEXT_SIZE_TPDE_OLD=$(size -A -d "${TPDE_OLD_BUILD_DIR}/${BENCH_NAMES[$idx]}_s" | grep ".text" | awk '{print $2}')
        TEXT_RATIO=$(awk "BEGIN{printf \"%.2f\n\",${TEXT_SIZE_TPDE}/${TEXT_SIZE_TPDE_OLD}}")
        echo "${BENCH_NUMBERS[$idx]} text clang: $TEXT_SIZE_CLANG" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde: $TEXT_SIZE_TPDE" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text tpde-old: $TEXT_SIZE_TPDE_OLD" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
        echo "${BENCH_NUMBERS[$idx]} text ratio: $TEXT_RATIO" | tee -a "${SCRIPT_DIR}/${OUT_FILE}"
    fi

done
