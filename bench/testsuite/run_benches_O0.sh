set +x
while read name; do
LLVM_O0_TIME=0
LLVM_O0_SIZE=0
LLVM_O1_TIME=0
LLVM_O1_SIZE=0
TPDE_TIME=0
TPDE_SIZE=0
TPDE_OLD_TIME=0
TPDE_OLD_SIZE=0
for ((i=0; i<3; ++i)); do
	TMP=`lit -v O0_build_llvm_O1/MultiSource/Benchmarks/$name -j 1`
	LLVM_O1_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum +=\\\$2} END {print ($LLVM_O1_TIME+sum)}"`
	LLVM_O1_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
for ((i=0; i<3; ++i)); do
	TMP=`lit -v O0_build_llvm_O0/MultiSource/Benchmarks/$name -j 1`
	LLVM_O0_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum +=\\\$2} END {print ($LLVM_O0_TIME+sum)}"`
	LLVM_O0_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
for ((i=0; i<3; ++i)); do
	TMP=`lit -v O0_build_tpde/MultiSource/Benchmarks/$name -j 1`
	TPDE_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum += \\\$2} END {print ($TPDE_TIME+sum)}"`
	TPDE_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
for ((i=0; i<3; ++i)); do
	TMP=`lit -v O0_build_tpde-old/MultiSource/Benchmarks/$name -j 1`
	TPDE_OLD_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum += \\\$2} END {print ($TPDE_OLD_TIME+sum)}"`
	TPDE_OLD_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
LLVM_O0_TIME=`awk "BEGIN {print ($LLVM_O0_TIME/3)}" < /dev/null`
LLVM_O1_TIME=`awk "BEGIN {print ($LLVM_O1_TIME/3)}" < /dev/null`
TPDE_OLD_TIME=`awk "BEGIN {print ($TPDE_OLD_TIME/3)}" < /dev/null`
TPDE_TIME=`awk "BEGIN {print ($TPDE_TIME/3)}" < /dev/null`
echo "$name,$LLVM_O0_TIME,$LLVM_O1_TIME,$TPDE_TIME,$TPDE_OLD_TIME,$LLVM_O0_SIZE,$LLVM_O1_SIZE,$TPDE_SIZE,$TPDE_OLD_SIZE"
done <../MultiSource-bench-names
