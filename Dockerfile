FROM ubuntu:16.04

# Install curl, sudo, bzip2, and git
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    sudo \
    bzip2 \
    git \
 && rm -rf /var/lib/apt/lists/*

# Use Tini as the init process with PID 1
RUN curl -Lso /tini https://github.com/krallin/tini/releases/download/v0.14.0/tini \
 && chmod +x /tini
ENTRYPOINT ["/tini", "--"]

# Create a working directory
RUN mkdir /app
WORKDIR /app

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' --shell /bin/bash user \
 && chown -R user:user /app
RUN echo "user ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-user
USER user

# Install Miniconda
RUN curl -so ~/miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-4.3.14-Linux-x86_64.sh \
 && chmod +x ~/miniconda.sh \
 && ~/miniconda.sh -b -p ~/miniconda \
 && rm ~/miniconda.sh

# Create a Python 3.6 environment
RUN /home/user/miniconda/bin/conda install conda-build \
 && /home/user/miniconda/bin/conda create -y --name py36 \
    python=3.6.0 numpy pyyaml scipy ipython mkl \
 && /home/user/miniconda/bin/conda clean -ya
ENV PATH=/home/user/miniconda/envs/py36/bin:$PATH \
    CONDA_DEFAULT_ENV=py36 \
    CONDA_PREFIX=/home/user/miniconda/envs/py36

# Install build tools
RUN sudo apt-get update && sudo apt-get install -y --no-install-recommends \
    build-essential \
 && sudo rm -rf /var/lib/apt/lists/*

# Install CFFI, Pillow, and NumPy
RUN conda install -y --name py36 \
    cffi pillow numpy \
 && conda clean -ya

# Install libwebp
RUN curl -sLo libwebp-0.6.0.tar.gz \
    https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-0.6.0.tar.gz \
 && tar xvzf libwebp-0.6.0.tar.gz \
 && rm libwebp-0.6.0.tar.gz \
 && cd libwebp-0.6.0 \
 && ./configure --enable-everything && make && sudo make install \
 && sudo sh -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/webp.conf' \
 && sudo ldconfig \
 && cd .. \
 && rm -rf libwebp-0.6.0

# Set the default command to python3
CMD ["python3"]
