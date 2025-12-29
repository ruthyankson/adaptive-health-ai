# Adaptive Health AI

This repository contains tooling and experiments for a health-focused data science project, with an emphasis on reproducibility (pinned environments, lock files, and container-ready workflows).

## Project Overview

Adaptive Health AI is a personal data science and machine learning project focused on building **user-adaptive, ethically grounded AI systems for health promotion and risk-aware decision support**.

The project explores how data-driven models can support personalized health insights while maintaining transparency, human oversight, and responsible AI practices. Rather than aiming for automated clinical decisions, the emphasis is on **decision support, learning, and user-centered design**.

Key themes include:
- Personalized and user-adaptive health modeling
- Ethical and responsible use of AI in health-related contexts
- Interpretable machine learning for risk awareness and behavior change
- Reproducible, research-ready engineering workflows

The repository is designed to be **modular and extensible**, supporting experimentation with public health datasets, baseline models, and lightweight deployment via APIs and containers.

---

## Reproducible Environment Tooling

### Create an Environment from the `conda-linux-64.lock` File

This project offers two ways to create a conda environment, but the recommended approach is to use the included explicit lock file, `conda-linux-64.lock` (platform: `linux-64`, kind: `explicit`), which pins exact package builds for fully deterministic, reproducible setups.

#### Option A (Recommended on Linux): Create the env directly from the explicit lock

On a Linux machine (CI/Docker or in a Linux container) where `health-ai` represents the target environment name:

```bash
conda create -n health-ai --file conda-linux-64.lock
conda activate health-ai
```

#### Option B: (Recommended on Windows/macOS): use `environment.yml` and then pin it

Because `conda-linux-64.lock` is explicitly locked for `linux-64`, it is not intended to be used directly on Windows or macOS.

For local development on Windows/macOS, create the environment from `environment.yml`:

```bash
conda env create -f environment.yml -n health-ai
conda activate health-ai
```

Then, to ensure consistency with the locked versions, use the `pin_env_versions.py` script to pin the installed/new package versions back into `environment.yml`. View the script documentation below for usage details.

---

### `pin_env_versions.py`

This script pins the package versions in `environment.yml` based on the versions currently installed in a specified conda environment, and can optionally generate an explicit `linux-64` lock file via `conda-lock`.

#### What it does

1. Reads `environment.yml`
2. Determines the target conda environment to inspect (via `--env` or the `name:` field in `environment.yml`)
3. Retrieves installed conda package versions from that environment (`conda list --json`)
4. Rewrites the `dependencies:` list in `environment.yml` so packages are pinned as `package=version`
5. If `--pin-pip` is provided, it also pins any `pip:` dependencies using `pip freeze` from the same environment
6. If `--lock-linux64` is provided, it generates a `linux-64` explicit lock file using `conda-lock`

This is useful for:
- consistent local development across machines
- deterministic CI/CD builds
- container builds that match a known dependency set

#### Prerequisites

Install these in the environment you will use to run the script (recommended: your project env, e.g., `health-ai`):

- `PyYAML`
- `conda-lock` (only required if generating lock files)

Example with `health-ai` env:

```bash
conda activate health-ai
conda install -c conda-forge pyyaml -y
python -m pip install conda-lock
```
#### Usage
A) Pin package versions in-place (recommended).

This updates `environment.yml` directly.

```bash
conda run -n health-ai python pin_env_versions.py -i \ environment.yml -n health-ai --inplace --pin-pip
```
B) Pin package versions to a new file

This writes to environment.pinned.yml without modifying the original.

```bash
conda run -n health-ai python pin_env_versions.py -i \ environment.yml -o environment.pinned.yml -n health-ai --pin-pip
```
C) Pin in-place and generate a linux-64 explicit lock file

```bash
conda run -n health-ai python pin_env_versions.py -i environment.yml -n health-ai --inplace \
  --pin-pip --lock-linux64 --lock-output conda-linux-64.lock
```
#### Outputs
- `environment.yml` (pinned in-place) or `environment.pinned.yml` (if using `--output`)
- `conda-linux-64.lock` (if using `--lock-linux64`)

Notes
- If your `environment.yml` includes `pip:` dependencies, use `--pin-pip` to ensure those are pinned as well.
- The lock file is generated for `linux-64` to support consistent CI and Docker builds, even if development is done on Windows or macOS.

To deactivate the conda environment when done:

```bash
conda deactivate
```
---

## Running the Project

You can run this project either as a Docker container (recommended for quick start) or locally using Conda (recommended for development).

---

### Option A: Run via Docker (Quick Start)

The container image is published to Docker Hub as:

- `doxelray/adaptive-health-ai`

#### Pull the latest image

```bash
docker pull doxelray/adaptive-health-ai:latest
```

#### Run the container

```bash
docker run -p 8000:8000 doxelray/adaptive-health-ai:latest
```
This starts the application and maps port 8000 from the container to your host machine.

#### Access the application
Open your web browser and navigate to `http://localhost:8000` to access the application.

### Option B: Run Locally with Conda (Development)  
1. Create and activate the conda environment as described in the "Reproducible Environment Tooling" section.  
2. Run the application:

```bash 
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

3. Access the application at `http://localhost:8000` in your web browser. **OR** Verify the service is running:

```bash
curl http://localhost:8000/health
```

Optionally, you can build and run the Docker container locally:

```bash
docker build -t adaptive-health-ai:local .
docker run -p 8000:8000 adaptive-health-ai:local
```

Then go back to step 3 to access the application.
