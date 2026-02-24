# syntax=docker/dockerfile:1
FROM fedora:42 AS build
ARG TARGETARCH
ARG NJOBS=4

# build dependencies
RUN dnf install -y clang-devel llvm-devel lld python binutils perl cmake ninja zlib zlib-devel git python3-lit ccache


ENV CCACHE_DIR=/ccache \
    CCACHE_MAXSIZE=20G \
    CCACHE_COMPRESS=1 \
    CCACHE_SLOPPINESS=time_macros

# Make sure ccache is used (choose one approach)
# 1) Preferred for CMake: set compiler launchers
# (You can also do this in CMakePresets.json instead.)
ENV CMAKE_C_COMPILER_LAUNCHER=ccache \
    CMAKE_CXX_COMPILER_LAUNCHER=ccache

WORKDIR /
RUN git clone --depth 1 --branch llvmorg-20.1.8 https://github.com/llvm/llvm-project.git

RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.db.in.tum.de >> ~/.ssh/known_hosts
RUN --mount=type=ssh git clone --recursive git@gitlab.db.in.tum.de:tpde/tpde2.git tpde

RUN git clone --recursive https://github.com/tpde2/tpde.git tpde-old

WORKDIR /tpde
RUN git switch salto




WORKDIR /llvm-project
RUN git config user.email "tpde@example.com" && git config user.name "TPDE" && git apply <  /tpde/llvm-20.616f2b685b06.patch && ln -s /tpde clang/lib/CodeGen/tpde2
RUN --mount=type=cache,target=/ccache CC=clang CXX=clang++ cmake -S llvm -B build_release -G 'Ninja' -DLLVM_ENABLE_PROJECTS='clang;flang' -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_RTTI=OFF -DLLVM_PARALLEL_LINK_JOBS=1 -DLLVM_TARGETS_TO_BUILD='X86;AArch64' -DLLVM_USE_LINKER='lld' -DLLVM_BUILD_LLVM_DYLIB=ON -DLLVM_LINK_LLVM_DYLIB=ON -DCLANG_BUILD_TOOLS=ON -DLLVM_INCLUDE_TESTS=OFF -DCMAKE_INSTALL_PREFIX=/llvm-install 
RUN --mount=type=cache,target=/ccache ninja -C build_release ${NJOBS:+-j $NJOBS} && cmake --build build_release --target install


# build TPDE tools?
WORKDIR /tpde
RUN --mount=type=cache,target=/ccache \
CC=clang CXX=clang++ cmake -DCMAKE_CXX_FLAGS="-Wno-error=unused-variable -Wno-error=unused-parameter" -B build -DCMAKE_BUILD_TYPE=Release -G Ninja \
 -DLLVM_ROOT=/llvm-install -DLLVM_DIR=/llvm-install/lib/cmake -DTPDE_CLANG=/llvm-install/bin/clang &&\
 ninja -C build ${NJOBS:+-j $NJOBS}

 WORKDIR /tpde-old
RUN --mount=type=cache,target=/ccache \
CC=clang CXX=clang++ cmake -DCMAKE_CXX_FLAGS="-Wno-error=unused-variable -Wno-error=unused-parameter" -B build -DCMAKE_BUILD_TYPE=Release -G Ninja \
 -DLLVM_ROOT=/llvm-install -DLLVM_DIR=/llvm-install/lib/cmake -DTPDE_CLANG=/llvm-install/bin/clang &&\
 ninja -C build ${NJOBS:+-j $NJOBS}

FROM fedora:42 AS benchmark

# Install dependencies for running the benchmarks
RUN dnf install -y libomp binutils-gold lld python perl cmake ninja zlib git python3-lit re2 boost-context abseil-cpp jemalloc zlib openssl-libs libedit awk libnsl libxcrypt-compat

# Latex to build figures
RUN dnf install -y latexmk jq texlive-base texlive-pdftex texlive-booktabs texlive-amsmath texlive-caption texlive-pgfplots texlive-xcolor texlive-framed texlive-microtype texlive-tikzpfeile texlive-tikz-ext texlive-preprint texlive-dvips

COPY --from=build /tpde /tpde
COPY --from=build /llvm-install /llvm-install
COPY --from=build /tpde-old /tpde-old


WORKDIR /
COPY bench /bench
WORKDIR /bench
RUN ln -s /llvm-install llvm && ln -s /tpde/build tpde && ln -s /tpde-old tpde-old

# clone llvm-test-suite
RUN git clone https://github.com/llvm/llvm-test-suite.git testsuite/llvm-test-suite
COPY llvm-test-suite.patch llvm-test-suite.patch
RUN cd testsuite/llvm-test-suite && git apply < ../../llvm-test-suite.patch && rm ../../llvm-test-suite.patch

WORKDIR /bench
CMD /bin/bash

FROM build AS uber

# Install dependencies for running the benchmarks
RUN dnf install -y libomp binutils-gold lld python perl cmake ninja zlib git python3-lit re2 boost-context abseil-cpp jemalloc zlib openssl-libs libedit awk libnsl libxcrypt-compat

# Latex to build figures
RUN dnf install -y latexmk jq texlive-base texlive-pdftex texlive-booktabs texlive-amsmath texlive-caption texlive-pgfplots texlive-xcolor texlive-framed texlive-microtype texlive-tikzpfeile texlive-tikz-ext texlive-preprint texlive-dvips

COPY --from=benchmark /bench /bench

WORKDIR /bench
CMD /bin/bash
