# NYX AI - LINUX COMPATIBLE DOCKERFILE
# Wine + MT5 + Signal Bridge Architecture

FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine
ENV PYTHONIOENCODING=utf-8

# Install system dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y \
    wine \
    wine32 \
    wine64 \
    winetricks \
    wget \
    curl \
    unzip \
    xvfb \
    x11-utils \
    python3 \
    python3-pip \
    git \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Configure Wine for silent operation
RUN winecfg --auto

# Download and install MT5 (silent installation)
RUN wget -O mt5setup.exe https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe && \
    wine mt5setup.exe /auto /quiet && \
    rm mt5setup.exe

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Create application directory
WORKDIR /app

# Copy application files
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/signals

# Set permissions
RUN chmod +x /app/*.sh

# Create supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create startup script
COPY start_docker.sh /usr/local/bin/start_docker.sh
RUN chmod +x /usr/local/bin/start_docker.sh

# Expose port for dashboard (if needed)
EXPOSE 8050

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/start_docker.sh"]

# Default command
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
