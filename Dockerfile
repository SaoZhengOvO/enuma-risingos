FROM ubuntu:24.04@sha256:9c7f200c07e3d4a03e7249d2c16bf66a51120fb876aa2242cf31451412543289
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    bc bison build-essential ca-certificates ccache curl file flex fontconfig g++-multilib \
    gcc-multilib git git-lfs gnupg gperf jq kmod lib32z1-dev libelf-dev liblz4-tool \
    libncurses-dev libssl-dev libx11-dev libxml2-utils lz4 openjdk-21-jdk-headless \
    patch perl pkg-config python3 python3-protobuf rsync unzip xz-utils xsltproc zip zstd \
    zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
RUN test "$(id -u ubuntu):$(id -g ubuntu)" = 1000:1000 && \
    mkdir -p /build && chown ubuntu:ubuntu /build
ENV HOME=/home/ubuntu
WORKDIR /build
USER 1000:1000
