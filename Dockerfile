# syntax=docker/dockerfile:1.7
FROM fedora:42 AS llvm-src
ARG LLVM_REF=llvmorg-20.1.8

RUN dnf install -y git cmake ninja clang-devel llvm-devel lld ccache python3-lit \
                  zlib zlib-devel perl binutils

ENV CCACHE_DIR=/ccache \
    CCACHE_MAXSIZE=20G \
    CCACHE_COMPRESS=1 \
    CCACHE_SLOPPINESS=time_macros \
    CMAKE_C_COMPILER_LAUNCHER=ccache \
    CMAKE_CXX_COMPILER_LAUNCHER=ccache

WORKDIR /
RUN git clone --depth 1 --branch ${LLVM_REF} https://github.com/llvm/llvm-project.git /llvm-project


# ----------------------------
# Stage 1: build vanilla LLVM (cached)
# ----------------------------
FROM llvm-src AS llvm-base
ARG TARGETARCH
ARG NJOBS=4

WORKDIR /llvm-project

# Configure into a cached build dir
RUN --mount=type=cache,id=llvm-build-${TARGETARCH},target=/llvm-project/build_release \
    --mount=type=cache,id=ccache-${TARGETARCH},target=/ccache \
    CC=clang CXX=clang++ \
    cmake -S llvm -B build_release -G Ninja \
      -DLLVM_ENABLE_PROJECTS='clang;flang' \
      -DCMAKE_BUILD_TYPE=Release \
      -DLLVM_ENABLE_RTTI=OFF \
      -DLLVM_PARALLEL_LINK_JOBS=1 \
      -DLLVM_TARGETS_TO_BUILD='X86;AArch64' \
      -DLLVM_USE_LINKER=lld \
      -DLLVM_BUILD_LLVM_DYLIB=ON \
      -DLLVM_LINK_LLVM_DYLIB=ON \
      -DCLANG_BUILD_TOOLS=ON \
      -DLLVM_INCLUDE_TESTS=OFF \
      -DCMAKE_INSTALL_PREFIX=/llvm-install

# Build vanilla LLVM into the same cached build dir
RUN --mount=type=cache,id=llvm-build-${TARGETARCH},target=/llvm-project/build_release \
    --mount=type=cache,id=ccache-${TARGETARCH},target=/ccache \
    ninja -C build_release ${NJOBS:+-j $NJOBS}

# (Optional) don’t install here — install after patch so /llvm-install matches tpde build
# RUN --mount=type=cache,id=llvm-build-${TARGETARCH},target=/llvm-project/build_release \
#     ninja -C build_release install


# ----------------------------
# Stage: fetch TPDE (separate so LLVM base cache doesn’t get invalidated)
# ----------------------------
FROM fedora:42 AS tpde-src
RUN dnf install -y git openssh-clients

RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan gitlab.db.in.tum.de >> ~/.ssh/known_hosts

# Pin TPDE to a ref for reproducibility (branch or commit SHA)
ARG TPDE_REF=40eac2790498d2d267a5a8c4236c7fb06fc90e97

RUN --mount=type=ssh \
    git clone --recursive git@gitlab.db.in.tum.de:tpde/tpde2.git /tpde && \
    cd /tpde && git checkout "${TPDE_REF}"

# If you also need the old tpde
RUN git clone --recursive https://github.com/tpde2/tpde.git /tpde-old


# ----------------------------
# Stage 2: apply patch + symlink, then incremental rebuild (reuses cached build dir)
# ----------------------------
FROM llvm-base AS llvm-tpde
ARG TARGETARCH
ARG NJOBS=4

# bring tpde sources + patch in
COPY --from=tpde-src /tpde /tpde
COPY --from=tpde-src /tpde-old /tpde-old

WORKDIR /llvm-project

# Apply patch + add symlink (this changes sources, but we’ll reuse the cached build dir)
RUN git config user.email "tpde@example.com" && \
    git config user.name "TPDE" && \
    git apply < /tpde/llvm-20.616f2b685b06.patch && \
    ln -s /tpde clang/lib/CodeGen/tpde2

# Incremental rebuild using the SAME cached build dir + ccache
RUN --mount=type=cache,id=llvm-build-${TARGETARCH},target=/llvm-project/build_release \
    --mount=type=cache,id=ccache-${TARGETARCH},target=/ccache \
    ninja -C build_release ${NJOBS:+-j $NJOBS} && \
    ninja -C build_release install


# ----------------------------
# Build TPDE tools against the installed LLVM (optional)
# ----------------------------
WORKDIR /tpde
RUN --mount=type=cache,id=ccache-${TARGETARCH},target=/ccache \
    CC=clang CXX=clang++ \
    cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_FLAGS="-Wno-error=unused-variable -Wno-error=unused-parameter" \
      -DLLVM_ROOT=/llvm-install -DLLVM_DIR=/llvm-install/lib/cmake \
      -DTPDE_CLANG=/llvm-install/bin/clang && \
    ninja -C build ${NJOBS:+-j $NJOBS}

WORKDIR /tpde-old
RUN --mount=type=cache,id=ccache-${TARGETARCH},target=/ccache \
    CC=clang CXX=clang++ \
    cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_FLAGS="-Wno-error=unused-variable -Wno-error=unused-parameter" \
      -DLLVM_ROOT=/llvm-install -DLLVM_DIR=/llvm-install/lib/cmake \
      -DTPDE_CLANG=/llvm-install/bin/clang && \
    ninja -C build ${NJOBS:+-j $NJOBS}


# ----------------------------
# Runtime / benchmark image (example)
# ----------------------------
FROM fedora:42 AS benchmark
RUN dnf install -y libomp binutils-gold lld python perl cmake ninja zlib git python3-lit \
                  re2 boost-context abseil-cpp jemalloc openssl-libs libedit awk libnsl libxcrypt-compat

COPY --from=llvm-tpde /tpde /tpde
COPY --from=llvm-tpde /tpde-old /tpde-old
COPY --from=llvm-tpde /llvm-install /llvm-install


WORKDIR /
COPY bench /bench
WORKDIR /bench
RUN ln -s /llvm-install llvm && ln -s /tpde/build tpde && ln -s /tpde-old/build tpde-old

# clone llvm-test-suite
RUN git clone https://github.com/llvm/llvm-test-suite.git testsuite/llvm-test-suite
COPY llvm-test-suite.patch llvm-test-suite.patch
RUN cd testsuite/llvm-test-suite && git apply < ../../llvm-test-suite.patch && rm ../../llvm-test-suite.patch

WORKDIR /bench
CMD /bin/bash