# Use the base vLLM TPU image
FROM vllm/vllm-tpu:v0.18.0

# Hardcode jaxlib wheel filename.
# Attention: must update this variable if jaxlib wheel filename changes
ARG JAXLIB_WHL_FILENAME="jaxlib-0.9.2.dev0+selfbuilt-cp312-cp312-manylinux_2_27_x86_64.whl"

# Copy the custom jaxlib wheel into the container
COPY ${JAXLIB_WHL_FILENAME} /tmp/

# Install the custom jaxlib, forcing reinstallation to overwrite any existing version.
RUN /usr/local/bin/python3.12 -m pip install --no-cache-dir --force-reinstall --no-deps /tmp/${JAXLIB_WHL_FILENAME}

# Optional: Clean up the wheel file after installation
RUN rm /tmp/${JAXLIB_WHL_FILENAME}
