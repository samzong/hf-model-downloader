# Download Tests

Run the offline suite:

```bash
uv run pytest -m "not network and not slow"
```

Run the Makefile smoke set:

```bash
make test
```

Run real downloads into a temporary directory:

```bash
QT_QPA_PLATFORM=offscreen uv run pytest tests/test_e2e_basic.py -v -s
```

Network tests are marked `network` and `slow`. They fail on download errors;
private-repository access failures are not treated as successful acceptance.

The Hugging Face model test uses the default `hf-mirror.com` endpoint and checks
weights, ONNX files, and `.gitattributes`. ModelScope tests use
`iic/nlp_structbert_sentence-similarity_chinese-tiny` and `swift/self-cognition`,
and check weights and raw dataset files in the repository directory.

`test_worker_lifecycle.py` uses local HTTP servers to verify cancellation during
stalled validation, preservation of child errors, repository-type hints in the
UI, and release of the worker only after the thread finishes. These tests do not
access external services.
