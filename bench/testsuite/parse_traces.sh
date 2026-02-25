set +x
while read name; do
python ../parse_trace_jsons.py $name build_llvm_O0/MultiSource/Benchmarks/$name build_llvm_O1/MultiSource/Benchmarks/$name build_tpde/MultiSource/Benchmarks/$name build_tpde_old/MultiSource/Benchmarks/$name true
done <../MultiSource-bench-names
