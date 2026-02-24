set +x
while read name; do
LLVM_TIME=0
LLVM_SIZE=0
TPDE_TIME=0
TPDE_SIZE=0
for ((i=0; i<3; ++i)); do
	TMP=`lit -v build_llvm/MultiSource/Benchmarks/$name -j 1`
	LLVM_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum +=\\\$2} END {print ($LLVM_TIME+sum)}"`
	LLVM_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
for ((i=0; i<3; ++i)); do
	TMP=`lit -v build_tpde/MultiSource/Benchmarks/$name -j 1`
	TPDE_TIME=`echo "$TMP" | grep "exec_time" | awk "{sum += \\\$2} END {print ($TPDE_TIME+sum)}"`
	TPDE_SIZE=`echo "$TMP" | grep "size..text" | awk "{sum +=\\\$2} END {print sum}"`
done
LLVM_TIME=`awk "BEGIN {print ($LLVM_TIME/3)}" < /dev/null`
TPDE_TIME=`awk "BEGIN {print ($TPDE_TIME/3)}" < /dev/null`
echo "$name,$LLVM_TIME,$TPDE_TIME,$LLVM_SIZE,$TPDE_SIZE"
done <../MultiSource-bench-names
