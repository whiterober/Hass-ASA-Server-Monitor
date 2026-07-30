# Wikily 生物数据自动导入助手  
## Tampermonkey 开发方案

---

### 1. 项目概述

**目标**：开发一个 Tampermonkey 用户脚本，允许用户在 Wikily 的“添加生物”（Add Creature）页面，通过导入从 ARK: Survival Ascended 游戏导出的 `.ini` 生物数据文件，自动解析并填充表单字段，从而节省手动输入的时间并避免录入错误。

**适用场景**：
- 玩家在游戏中通过“导出恐龙”功能生成 `.ini` 文件（位于 `ShooterGame/Saved/DinoExports/`）。
- 用户打开 Wikily 的添加生物页面（例如 `https://wikily.gg/zh-cn/ark-survival-ascended/profile/xxx/` 并点击“加生物”）。
- 脚本提供一个上传按钮，用户选择 `.ini` 文件后，脚本自动解析并填充所有字段（恐龙种类、等级、各项属性等）。

**技术栈**：
- Tampermonkey API（用户脚本平台）
- 原生 JavaScript（ES6+）
- FileReader API（读取本地文件）
- 正则表达式或简单解析器（解析 `.ini` 格式）
- DOM 操作 + 事件触发（适配 React 等框架）

---

### 2. 需求分析

#### 2.1 功能需求
- **文件上传入口**：在页面合适位置（如表单上方）添加一个“导入 .ini 文件”按钮或拖拽区域。
- **文件解析**：读取 `.ini` 文件内容，提取以下关键字段：
  - 恐龙种类（`DinoClass` 或 `ClassName`）
  - 生物名称（可选，用于标记）
  - 等级（`BaseLevel` 或 `Level`）
  - 各项属性数值（生命、耐力、氧气、食物、重量、近战、速度，含驯服后加成）
  - 驯服有效性（若已驯服）
- **表单填充**：将解析出的数据填入对应的下拉菜单、输入框，并触发框架的变更事件，确保 `onChange` 等处理生效。
- **状态提示**：显示导入成功/失败消息，并说明解析到的数据。

#### 2.2 非功能需求
- **兼容性**：仅在 `wikily.gg` 域名下运行，且仅在包含“添加生物”表单的页面激活。
- **性能**：文件解析应快速（< 100ms 对于典型文件大小）。
- **安全性**：不上传文件数据，纯本地处理。
- **易用性**：界面简洁，操作流程清晰。

---

### 3. 技术方案设计

#### 3.1 整体流程
```
用户点击“导入文件”按钮
       ↓
选择 .ini 文件
       ↓
读取文件内容 (FileReader)
       ↓
解析 .ini 文本 → 提取数据对象
       ↓
根据数据对象填充表单元素
       ↓
触发变更事件 → 表单更新
       ↓
显示成功提示
```

#### 3.2 关键技术点

##### 3.2.1 文件读取
使用 `FileReader` 读取文本文件：
```javascript
function readFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e.target.error);
        reader.readAsText(file);
    });
}
```

##### 3.2.2 .ini 文件解析
ARK 导出的 `.ini` 文件结构示例（基于官方导出格式）：
```ini
[Dino]
DinoClass=Blueprint'/Game/PrimalEarth/Dinos/Rex/Rex_Character_BP.Rex_Character_BP'
DinoNameTag=MyRex
BaseLevel=150
Stats[0]=1100.0     ; 生命
Stats[1]=360.0      ; 耐力
Stats[2]=150.0      ; 氧气
Stats[3]=6000.0     ; 食物
Stats[4]=450.0      ; 重量
Stats[5]=100.0      ; 近战
Stats[6]=100.0      ; 速度
TamedEffectiveness=0.9978
```

解析策略：
- 按行读取，跳过空行和注释（`;` 开头）。
- 使用正则表达式提取键值对：`/^(\w+(?:\[\d+\])?)\s*=\s*(.*)$/`。
- 对于 `Stats[0]` 等，将 `Stats` 数组映射到具体属性（需要知道顺序：0-生命, 1-耐力, 2-氧气, 3-食物, 4-重量, 5-近战, 6-速度）。
- 提取 `DinoClass` 中的类名（例如 `Rex_Character_BP`）以匹配 Wikily 的下拉选项。

##### 3.2.3 恐龙种类匹配
Wikily 的下拉菜单通常使用 `<select>` 元素，`<option>` 的 `value` 可能包含内部标识。我们需要将 `DinoClass` 映射到正确的 `value`。可能的做法：
- 从 `DinoClass` 中提取生物名称（如 `Rex`），然后查找下拉选项中包含该名称的选项。
- 如果匹配失败，让用户手动选择（记录日志）。

##### 3.2.4 表单填充与事件触发
由于 Wikily 可能使用 React，直接设置 `value` 不会触发 `onChange`。必须派发原生事件：
```javascript
function fillInput(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    // 某些框架需要 blur 事件以触发验证
    element.dispatchEvent(new Event('blur', { bubbles: true }));
}
```
对于 `<select>`，同样需要触发 `change` 事件。

##### 3.2.5 UI 植入
在页面加载后，通过 DOM 操作在合适容器（例如表单前）添加一个 `div`，包含文件上传按钮和状态显示区。
使用 `MutationObserver` 或简单的 `setTimeout` 等待表单加载完成。

---

### 4. 详细实现步骤

#### 4.1 项目目录结构（脚本内嵌，无外部文件）
```
// ==UserScript==
// @name         Wikily 生物数据自动导入助手
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  从 ARK 导出的 .ini 文件自动填充添加生物表单
// @author       YourName
// @match        https://wikily.gg/zh-cn/ark-survival-ascended/profile/*
// @grant        none
// @require      none
// ==/UserScript==
```
- 脚本仅在 `profile` 页面下运行，因为“加生物”操作在此路径。

#### 4.2 核心代码模块

##### 4.2.1 等待页面元素就绪
```javascript
function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }
        const observer = new MutationObserver(() => {
            if (document.querySelector(selector)) {
                resolve(document.querySelector(selector));
                observer.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`元素 ${selector} 未找到`));
        }, timeout);
    });
}
```

##### 4.2.2 植入上传按钮
```javascript
async function injectUI() {
    try {
        // 找到表单的父容器，例如一个具有特定类名的 div
        const formContainer = await waitForElement('.add-creature-form'); // 需要实际类名
        const uploadDiv = document.createElement('div');
        uploadDiv.style.margin = '10px 0';
        uploadDiv.innerHTML = `
            <label for="fileInput" style="cursor:pointer;background:#4CAF50;color:white;padding:8px 16px;border-radius:4px;">
                导入 .ini 文件
            </label>
            <input type="file" id="fileInput" accept=".ini" style="display:none;">
            <span id="statusMsg" style="margin-left:10px;color:#333;"></span>
        `;
        formContainer.parentNode.insertBefore(uploadDiv, formContainer);
        document.getElementById('fileInput').addEventListener('change', handleFileSelect);
    } catch (error) {
        console.error('注入UI失败', error);
    }
}
```

##### 4.2.3 文件选择处理
```javascript
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    const status = document.getElementById('statusMsg');
    status.textContent = '正在解析...';
    try {
        const content = await readFile(file);
        const data = parseIni(content);
        await fillForm(data);
        status.textContent = '✅ 导入成功！';
    } catch (err) {
        status.textContent = '❌ 导入失败: ' + err.message;
        console.error(err);
    }
}
```

##### 4.2.4 解析 .ini 文件
```javascript
function parseIni(text) {
    const lines = text.split('\n');
    const result = { stats: [] };
    for (let line of lines) {
        line = line.trim();
        if (!line || line.startsWith(';')) continue;
        const match = line.match(/^(\w+(?:\[\d+\])?)\s*=\s*(.*)$/);
        if (!match) continue;
        const key = match[1];
        const value = match[2].trim();
        if (key === 'DinoClass') {
            // 提取最后一部分类名
            const parts = value.split('.');
            result.dinoClass = parts[parts.length - 1].replace(/_C$/, ''); // 移除 _C
        } else if (key === 'DinoNameTag') {
            result.name = value;
        } else if (key === 'BaseLevel') {
            result.level = parseInt(value, 10);
        } else if (key.startsWith('Stats[')) {
            const idx = parseInt(key.match(/\d+/)[0], 10);
            result.stats[idx] = parseFloat(value);
        } else if (key === 'TamedEffectiveness') {
            result.tamedEff = parseFloat(value);
        }
    }
    return result;
}
```

##### 4.2.5 填充表单
假设已知表单元素的 ID 或选择器（需实际调研 Wikily 页面结构）。示例：
```javascript
async function fillForm(data) {
    // 1. 选择恐龙种类
    const dinoSelect = document.querySelector('select[name="dinoType"]'); // 示例
    if (dinoSelect) {
        const options = dinoSelect.options;
        for (let opt of options) {
            if (opt.text.includes(data.dinoClass) || opt.value.includes(data.dinoClass)) {
                dinoSelect.value = opt.value;
                dinoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                break;
            }
        }
    }

    // 2. 填写等级
    const levelInput = document.querySelector('input[name="level"]');
    if (levelInput && data.level) fillInput(levelInput, data.level);

    // 3. 填写各项属性 (假设 name 为 health, stamina, ...)
    const statNames = ['health', 'stamina', 'oxygen', 'food', 'weight', 'melee', 'speed'];
    data.stats.forEach((val, idx) => {
        if (idx < statNames.length) {
            const input = document.querySelector(`input[name="${statNames[idx]}"]`);
            if (input) fillInput(input, val);
        }
    });

    // 4. 驯服有效性 (如果有)
    if (data.tamedEff) {
        const effMin = document.querySelector('input[name="tamingEffMin"]');
        const effMax = document.querySelector('input[name="tamingEffMax"]');
        if (effMin) {
            const effPercent = Math.round(data.tamedEff * 100);
            fillInput(effMin, effPercent);
            if (effMax) fillInput(effMax, effPercent);
        }
    }
}
```

##### 4.2.6 辅助函数 fillInput
```javascript
function fillInput(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
}
```

#### 4.3 启动脚本
```javascript
(function() {
    'use strict';
    // 等待页面完全加载
    if (document.readyState === 'complete') {
        injectUI();
    } else {
        window.addEventListener('load', injectUI);
    }
})();
```

---

### 5. 测试与调试

#### 5.1 环境准备
- 安装 Tampermonkey 浏览器扩展。
- 在 Wikily 网站登录并进入自己的 profile 页面，点击“加生物”进入表单页。

#### 5.2 测试用例
- **正常情况**：选择一个有效的 `.ini` 文件，验证所有字段正确填充。
- **缺少某些字段**：如未导出有效性，脚本应跳过并提示。
- **未知恐龙种类**：脚本无法匹配时，记录警告，让用户手动选择。

#### 5.3 调试工具
- 使用浏览器开发者工具（F12）查看 Console 日志。
- 在脚本中添加 `console.log` 输出解析数据。
- 使用 Tampermonkey 的“编辑”功能快速修改脚本并重新加载。

---

### 6. 部署与使用说明

#### 6.1 安装脚本
1. 复制完整脚本代码。
2. 打开 Tampermonkey 仪表盘，点击“+”新建脚本。
3. 粘贴代码，保存（Ctrl+S）。
4. 确保脚本已启用。

#### 6.2 使用步骤
1. 在游戏中导出目标生物的 `.ini` 文件（物品栏轮盘 → 导出恐龙）。
2. 打开 Wikily 的 profile 页面，点击“加生物”。
3. 在表单上方点击“导入 .ini 文件”按钮，选择刚导出的文件。
4. 脚本自动填充表单，检查填充是否正确后提交。

#### 6.3 注意事项
- 脚本依赖于 Wikily 页面的实际 DOM 结构，如果网站改版，可能需要更新选择器。
- 建议定期检查脚本兼容性。
- 确保导入的文件为 UTF-8 编码（游戏默认）。

---

### 7. 扩展与优化建议

- **批量导入**：支持一次性导入多个文件，或者解析存档文件批量提取。
- **自动识别野生/驯服模式**：根据 `TamedEffectiveness` 是否存在自动切换标签。
- **自定义映射**：当自动匹配恐龙种类失败时，允许用户从下拉列表中选择并记住映射。
- **云端同步**：将导入数据保存到本地存储，方便复用。

---

### 8. 附录：完整脚本示例

以下提供一份完整可用的脚本框架（部分选择器为占位，需实际调整）：

```javascript
// ==UserScript==
// @name         Wikily Dino Importer
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Import ARK .ini dino export into Wikily add creature form
// @author       YourName
// @match        https://wikily.gg/zh-cn/ark-survival-ascended/profile/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // --- 等待元素 ---
    function waitForElement(selector, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const el = document.querySelector(selector);
            if (el) return resolve(el);
            const observer = new MutationObserver(() => {
                const el2 = document.querySelector(selector);
                if (el2) {
                    resolve(el2);
                    observer.disconnect();
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`Element ${selector} not found`));
            }, timeout);
        });
    }

    // --- 文件读取 ---
    function readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e.target.error);
            reader.readAsText(file);
        });
    }

    // --- 解析 .ini ---
    function parseIni(text) {
        const lines = text.split('\n');
        const result = { stats: [] };
        for (let line of lines) {
            line = line.trim();
            if (!line || line.startsWith(';')) continue;
            const match = line.match(/^(\w+(?:\[\d+\])?)\s*=\s*(.*)$/);
            if (!match) continue;
            const key = match[1];
            const value = match[2].trim();
            if (key === 'DinoClass') {
                const parts = value.split('.');
                result.dinoClass = parts[parts.length - 1].replace(/_C$/, '');
            } else if (key === 'DinoNameTag') {
                result.name = value;
            } else if (key === 'BaseLevel') {
                result.level = parseInt(value, 10);
            } else if (key.startsWith('Stats[')) {
                const idx = parseInt(key.match(/\d+/)[0], 10);
                result.stats[idx] = parseFloat(value);
            } else if (key === 'TamedEffectiveness') {
                result.tamedEff = parseFloat(value);
            }
        }
        return result;
    }

    // --- 填充输入框（触发事件）---
    function fillInput(element, value) {
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
    }

    // --- 填充表单 ---
    async function fillForm(data) {
        // 此处需要根据实际页面结构调整选择器
        // 示例：假设表单有这些 name 或 id
        const dinoSelect = document.querySelector('select[name="dinoType"]');
        if (dinoSelect && data.dinoClass) {
            for (let opt of dinoSelect.options) {
                if (opt.text.toLowerCase().includes(data.dinoClass.toLowerCase()) ||
                    opt.value.toLowerCase().includes(data.dinoClass.toLowerCase())) {
                    dinoSelect.value = opt.value;
                    dinoSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    break;
                }
            }
        }

        const levelInput = document.querySelector('input[name="level"]');
        if (levelInput && data.level) fillInput(levelInput, data.level);

        const statNames = ['health', 'stamina', 'oxygen', 'food', 'weight', 'melee', 'speed'];
        if (data.stats && data.stats.length) {
            data.stats.forEach((val, idx) => {
                if (idx < statNames.length) {
                    const input = document.querySelector(`input[name="${statNames[idx]}"]`);
                    if (input) fillInput(input, val);
                }
            });
        }

        if (data.tamedEff) {
            const effMin = document.querySelector('input[name="tamingEffMin"]');
            const effMax = document.querySelector('input[name="tamingEffMax"]');
            if (effMin) {
                const effPercent = Math.round(data.tamedEff * 100);
                fillInput(effMin, effPercent);
                if (effMax) fillInput(effMax, effPercent);
            }
        }
    }

    // --- 文件选择处理 ---
    async function handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        const status = document.getElementById('statusMsg');
        status.textContent = '正在解析...';
        try {
            const content = await readFile(file);
            const data = parseIni(content);
            await fillForm(data);
            status.textContent = '✅ 导入成功！';
        } catch (err) {
            status.textContent = '❌ 导入失败: ' + err.message;
            console.error(err);
        }
    }

    // --- 注入 UI ---
    async function injectUI() {
        try {
            // 等待表单容器出现（需替换实际选择器）
            const formContainer = await waitForElement('.add-creature-form'); // 示例类名
            const uploadDiv = document.createElement('div');
            uploadDiv.style.margin = '10px 0';
            uploadDiv.innerHTML = `
                <label for="fileInput" style="cursor:pointer;background:#4CAF50;color:white;padding:8px 16px;border-radius:4px;display:inline-block;">
                    导入 .ini 文件
                </label>
                <input type="file" id="fileInput" accept=".ini" style="display:none;">
                <span id="statusMsg" style="margin-left:10px;color:#333;"></span>
            `;
            formContainer.parentNode.insertBefore(uploadDiv, formContainer);
            document.getElementById('fileInput').addEventListener('change', handleFileSelect);
        } catch (error) {
            console.error('注入UI失败', error);
        }
    }

    // --- 启动 ---
    if (document.readyState === 'complete') {
        injectUI();
    } else {
        window.addEventListener('load', injectUI);
    }
})();
```

---

### 9. 结束语

本方案提供了完整的开发指南，通过 Tampermonkey 脚本实现了从 ARK 导出文件到 Wikily 表单的自动化导入。开发者只需根据实际页面结构调整选择器即可投入使用。该脚本可显著提升繁殖数据录入效率，是方舟玩家的实用辅助工具。如有问题，欢迎在社区讨论。