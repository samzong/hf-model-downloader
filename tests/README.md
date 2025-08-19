# E2E Tests for HF Model Downloader

## 运行测试

### 运行所有测试
```bash
uv run pytest
```

### 运行特定测试
```bash
# 运行 HuggingFace 下载测试
uv run pytest tests/test_e2e_basic.py::TestBasicE2E::test_huggingface_tiny_model -v -s

# 运行取消下载测试
uv run pytest tests/test_e2e_basic.py::TestBasicE2E::test_cancel_download -v -s

# 运行 ModelScope 测试（可能需要认证）
uv run pytest tests/test_e2e_basic.py::TestBasicE2E::test_modelscope_model -v -s
```

### 查看详细输出
```bash
uv run pytest -v -s
```

## 测试说明

### ✅ 工作的测试
- `test_huggingface_tiny_model`: 下载极小的 HuggingFace 模型
- `test_cancel_download`: 测试取消下载功能

### ⚠️ 可能跳过的测试
- `test_modelscope_model`: ModelScope 模型下载（可能需要认证）
- `test_modelscope_dataset`: ModelScope 数据集下载（这是我们修复的功能）

### 🔧 已修复的问题
- ModelScope 下载函数现在正确传递 `repo_type` 参数
- 支持下载 ModelScope 数据集（不仅仅是模型）

## 测试文件
- `test_e2e_basic.py`: 基础端到端测试
- `pytest.ini`: pytest 配置文件

## 注意事项
- 测试使用真实网络下载
- 选择了极小的模型/数据集以确保测试速度
- ModelScope 测试可能会因为需要认证而跳过