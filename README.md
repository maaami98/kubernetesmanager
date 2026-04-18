# Kubernetes Manager

`kubernetesmanager` contains the interactive `km` script for managing Kubernetes clusters with an intuitive folder-like shell.

## Install

Use the install script hosted on GitHub:

```bash
curl -fsSL https://github.com/<OWNER>/<REPO>/raw/main/kubernetesmanager/install.sh | sh
```

Replace `<OWNER>` and `<REPO>` with your GitHub user/org and repository name.

## Usage

After installation, run:

```bash
km
```

## Notes

- The installer attempts to install `km` into `/usr/local/bin` when possible.
- If `/usr/local/bin` is not writable, it installs into `~/.local/bin` and updates your shell RC file.
- `kubectl` must be installed and available in your PATH.
- `pyyaml` is required by the script.
