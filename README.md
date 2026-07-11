# Knowbase

## 项目介绍

Knowbase 是一个前后端一体化的知识库项目。

- 后端基于 FastAPI
- 前端位于 `ui/`，由后端统一托管
- 项目主入口位于根目录 `main.py`

## 目录介绍

```text
knowbase/
  main.py
  bootstrap.py
  internal/
  config/
  ui/
  docs/
```

- `main.py`: 项目启动入口
- `bootstrap.py`: 应用装配入口
- `internal/`: 后端内部实现
- `config/`: 配置文件
- `ui/`: 前端源码
- `docs/`: 项目文档

## 启动方法

1. 准备配置文件：

```bash
cp config/app.example.yaml config/app.yaml
```

2. 补全 `config/app.yaml`

3. 在项目根目录启动：

```bash
python main.py --config config/app.yaml
```

启动后可访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`

## 文档位置

- [docs/knowbase.md](./docs/knowbase.md)
- [docs/flows.md](./docs/flows.md)
- [docs/code_structure.md](./docs/code_structure.md)
- [docs/runtime.md](./docs/runtime.md)
