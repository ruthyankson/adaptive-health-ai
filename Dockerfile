# # Use a minimal conda base (good for explicit lock installs)
# FROM continuumio/miniconda3:24.7.1-0

# # Prevent interactive prompts
# ENV DEBIAN_FRONTEND=noninteractive

# WORKDIR /app

# # Copy your explicit lock file
# COPY conda-linux-64.lock /tmp/conda-linux-64.lock

# # Create a dedicated environment from the explicit lock file
# # (explicit lock file is linux-64, perfect for Docker)
# RUN conda create -y -n health-ai --file /tmp/conda-linux-64.lock && \
#     conda clean --all -f -y

# # Ensure the environment is used by default
# SHELL ["conda", "run", "-n", "health-ai", "/bin/bash", "-c"]

# # Copy application code
# COPY app/ app/

# # Expose FastAPI port
# EXPOSE 8000

# # Run FastAPI (adjust module path if needed)
# # CMD ["conda", "run", "-n", "health-ai", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM continuumio/miniconda3:24.7.1-0

WORKDIR /app

COPY conda-linux-64.lock /tmp/conda-linux-64.lock

RUN conda create -y -n health-ai --file /tmp/conda-linux-64.lock && \
    conda clean --all -f -y

COPY app/ app/

# Use the env by default without `conda run`
ENV PATH=/opt/conda/envs/health-ai/bin:$PATH

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
