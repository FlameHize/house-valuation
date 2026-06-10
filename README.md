# 房产估值工具 🏠

基于 Streamlit 的个人房产估值分析工具，包含三个核心模型：DCF 现金流估值、Hedonic 特征价格调价、提前还贷分析。

## 功能概览

### 📊 房产现金流估值模型（DCF）

计算小区居住公允价值，作为调价模型的基准价。

- **购房方案输入**：总房价、首付比例、贷款利率、贷款年限
- **估值假设**：月租金、持有成本、增长率、通胀率、折现率、折旧率、人口比例、持有期
- **税费参数**：契税、中介费、增值税、个人所得税
- **输出指标**：
  - 居住公允价值（省租金现值 + 期末残值）
  - 净现值 (NPV) — 判断买房 vs 租房哪个更划算
  - 盈亏平衡房价
  - 敏感性分析（折现率 × 增长率矩阵）
  - 年度现金流与累积 NPV 曲线
- **一键生成报告**：图文并茂的 PNG 报告下载

### 📐 特征价格调价模型（Hedonic）

在 DCF 小区公允价值的基础上，逐项调整房源特征得到最终估值。

- **基准价**：自动同步 DCF 公允价值（支持手动覆盖）
- **调整因子**（11 项）：
  - 楼层、朝向、南向开间数、通透性、装修
  - 房龄、得房率、景观视野、噪音、户型格局、梯户比
- **输出**：调整明细表、各因子贡献瀑布图、最终估值
- **联动**：按最终估值重算月供和购房费用

### 💰 提前还贷分析

评估提前还贷对现金流的影响，对比缩短年限与减少月供两种方案。

- **方案 A：缩短年限** — 月供不变，更快还清
- **方案 B：减少月供** — 年限不变，月供降低
- **还贷 vs 理财对比** — 还贷等效收益 vs 理财预期收益
- **推荐建议** — 根据参数自动判断哪种方案更优

## 快速开始

### 方式一：本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/house-valuation.git
cd house-valuation

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 运行
streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可。

### 方式二：Docker

```dockerfile
FROM python:3.12-slim

RUN apt update && apt install -y libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info fonts-wqy-microhei && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t house-valuation .
docker run -p 8501:8501 house-valuation
```

## 页面导航

| 页面 | 路径 | 说明 |
|------|------|------|
| 房产估值 | `pages/home.py` | DCF 现金流估值模型 |
| 房源调整 | `pages/1_hedonic.py` | 特征价格调价模型 |
| 提前还贷 | `pages/2_prepayment.py` | 提前还贷分析 |

## 技术栈

- **前端/后端**：Streamlit
- **数值计算**：NumPy, Matplotlib
- **报告生成**：Markdown → weasyprint → PyMuPDF → PIL
- **Python**：3.10+

## 项目结构

```
house-valuation/
├── app.py                    # 导航入口
├── pages/
│   ├── home.py               # DCF 现金流估值
│   ├── 1_hedonic.py          # Hedonic 特征价格调价
│   └── 2_prepayment.py       # 提前还贷分析
├── valuation/
│   ├── dcf.py                # DCF 计算核心
│   ├── hedonic.py            # Hedonic 调价计算 + 系数表
│   ├── prepayment.py         # 提前还贷计算
│   └── report_utils.py       # 报告生成工具（PNG）
├── requirements.txt
└── README.md
```

## 报告生成

每个页面侧边栏底部有 **生成报告** 按钮，点击后生成完整分析报告（PNG 格式），可直接下载到本地。

报告内容包含：
- 所有输入参数汇总表
- 核心计算指标与结论
- 敏感性分析矩阵及热力图
- 现金流/调价/对比可视化图表
- 免责声明

## Nginx 反向代理（可选）

如部署到云服务器，参考以下 Nginx 配置：

```nginx
location /house/ {
    proxy_pass http://127.0.0.1:8501/house/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}
```

Streamlit 需配置 `baseUrlPath`：

```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
baseUrlPath = "/house"
```

## 免责声明

本工具仅供个人参考，不构成投资建议。估值结果基于用户输入的假设参数，实际市场情况可能存在偏差。房产投资需综合考虑地理位置、政策变化、市场供需等多方面因素。
