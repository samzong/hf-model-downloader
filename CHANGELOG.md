# CHANGELOG

<!-- version list -->

## v0.3.2 (2025-08-19)

### Chores

- **ci**: Prioritize GH_PAT secret and add debug checks in workflows and scripts
  ([`714294a`](https://github.com/samzong/hf-model-downloader/commit/714294a8821f60d9c6c20e96b7a469da23a25521))


## v0.3.1 (2025-08-19)

### Chores

- **workflows**: Update token from GH_TOKEN to GH_PAT for release authentication
  ([`809ed88`](https://github.com/samzong/hf-model-downloader/commit/809ed8883b1efca2941d8bdc5ef64d5e2168199d))


## v0.3.0 (2025-08-19)

### Features

- Improve workflow trigger mechanism
  ([`3df93a1`](https://github.com/samzong/hf-model-downloader/commit/3df93a1bf720e5063d8d7bf2e1dda1fec36a6a5d))


## v0.2.0 (2025-08-19)

### Bug Fixes

- **makefile**: Correct dmg filename and export VERSION for homebrew update script
  ([`f0e94f7`](https://github.com/samzong/hf-model-downloader/commit/f0e94f77bfe0e149261e6c0b598934b9704bcc59))

### Features

- **ci**: Add multi-platform build and release workflows with macOS and Windows support
  ([`e9f560f`](https://github.com/samzong/hf-model-downloader/commit/e9f560f3516c3525a70d39c525458d1d19d1ec6d))


## v0.1.1 (2025-08-19)

### Chores

- **ci**: Add debug info to release workflow and improve homebrew update script handling
  ([`8d35874`](https://github.com/samzong/hf-model-downloader/commit/8d35874a986c9a3b823a0fbdd8dd7231f614fea8))


## v0.1.0 (2025-08-18)

### Bug Fixes

- **build**: Correct Makefile syntax errors in define blocks
  ([`139886f`](https://github.com/samzong/hf-model-downloader/commit/139886f7093d2637deec281fa6c00f602f46f9a4))

### Build System

- **release**: Intergrate python-semantic-release
  ([`f64b7ef`](https://github.com/samzong/hf-model-downloader/commit/f64b7efcd1a52bfd5de303cbb29064602a58d063))

### Features

- **homebrew**: Add modular script and Makefile check for Homebrew Cask update
  ([`2f9c902`](https://github.com/samzong/hf-model-downloader/commit/2f9c902080686e01d5155d0a9db2f2bb77f99362))

### Refactoring

- **ci**: Enhance release workflow to output version and release status
  ([`7889dcf`](https://github.com/samzong/hf-model-downloader/commit/7889dcfdcf9f20b5cc97ca84e841330b75a23a51))

- **makefile**: Improve maintainability with enhanced logging, validations, and organized variables
  ([`d6c4372`](https://github.com/samzong/hf-model-downloader/commit/d6c43722647c0d2f4c51310a927bd2ccb9118928))


## v0.0.7 (2025-08-18)

### Documentation

- **license**: Add initial MIT license file
  ([`4cac811`](https://github.com/samzong/hf-model-downloader/commit/4cac811b63f014ea47eb40bcb4d38872ea164a9d))

### Features

- **python**: Add environment config, python 3.13, and dependencies for HF model downloader
  ([`c8d7975`](https://github.com/samzong/hf-model-downloader/commit/c8d79752f7b851002ecb3a55d3f3042ec3a4382e))

### Refactoring

- **downloader**: Add LoggerManager to unify log handler management and prevent leaks
  ([`ca6ac84`](https://github.com/samzong/hf-model-downloader/commit/ca6ac841ed7e2fe0095eefdb6775766192f09e5a))

- **Makefile**: Update SHA256 handling for Homebrew Cask to use new on_arm/on_intel format
  ([`f7d8cc4`](https://github.com/samzong/hf-model-downloader/commit/f7d8cc448b581457d993492a362b976bf560e270))


## v0.0.6 (2025-06-11)


## v0.0.5 (2025-06-11)

### Bug Fixes

- Use architecture-specific executable name for Windows builds
  ([`25cdcc8`](https://github.com/samzong/hf-model-downloader/commit/25cdcc8aef10a7e2514cba6ced82347845fe3b3b))

### Documentation

- **claimed**: Add CLAUDE.md with development and architecture guidance
  ([`0e9a596`](https://github.com/samzong/hf-model-downloader/commit/0e9a5964763203c0c0793a79e711f1f75c7e34a8))

- **readme**: Add DeepWiki badge link to project header
  ([`a047f5e`](https://github.com/samzong/hf-model-downloader/commit/a047f5eff556c299f8203b5f6c5fea8f65b85b60))


## v0.0.4 (2025-03-05)


## v0.0.2 (2025-01-16)


## v0.0.1 (2025-01-15)

- Initial Release
