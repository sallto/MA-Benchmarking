git clone --depth 1 --branch llvmorg-20.1.8 https://github.com/llvm/llvm-project.git
git clone --recursive git@gitlab.db.in.tum.de:tpde/tpde2.git tpde2
cd tpde2
git switch salto
cd ..
cd llvm-project
git apply ../tpde2/llvm-20.616f2b685b06.patch
ln -s ~/Code/benchmarking/tpde2 clang/lib/CodeGen/tpde2
CC=clang CXX=clang++ cmake -S llvm -B build_release -G 'Ninja' -DLLVM_ENABLE_PROJECTS='clang;flang' -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_RTTI=OFF -DLLVM_PARALLEL_LINK_JOBS=1 -DLLVM_TARGETS_TO_BUILD='X86;AArch64' -DLLVM_USE_LINKER='lld' -DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON -DCLANG_BUILD_TOOLS=ON -DLLVM_INCLUDE_TESTS=OFF -DLLVM_CCACHE_BUILD=On -DCMAKE_INSTALL_PREFIX=llvm-install 

git clone https://github.com/llvm/llvm-test-suite.git testsuite/llvm-test-suite
