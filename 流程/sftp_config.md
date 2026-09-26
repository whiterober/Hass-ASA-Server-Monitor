# HA 服务器 SFTP 连接配置

| 参数 | 值 |
|------|-----|
| 主机 | whiterober.mycloudnas.com |
| 协议 | SFTP |
| 端口 | 25322 |
| 用户名 | root |
| 密码 | 1219Wu1219@ |

## ⚠️ 同步规则

**XFtp 已实时同步**（无需手动上传）：
| 本地 | 远程 |
|------|------|
| `A:\NetSarang\Xftp 8\Temporary\configuration.yaml` | `/config/configuration.yaml` |
| `A:\NetSarang\Xftp 8\Temporary\lovelace` | `/config/lovelace` |
| `A:\NetSarang\Xftp 8\Temporary\lovelace.lovelace` | `/config/lovelace.lovelace` |
| `A:\NetSarang\Xftp 8\Temporary\apps.yaml` | `/config/apps.yaml` |
| `A:\NetSarang\Xftp 8\Temporary\scripts.yaml` | `/config/scripts.yaml` |

**需手动 SFTP 上传**（非 XFtp 同步范围）：
| 本地 | 远程 |
|------|------|
| `A:\NetSarang\Xftp 8\Temporary\*.json` | `/config/` |
| `A:\NetSarang\Xftp 8\Temporary\www\**\*` | `/config/www/` |

## 命令行上传示例

```bash
# Python 单文件上传
python -c "
import paramiko
c=paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('whiterober.mycloudnas.com',port=25322,username='root',password='1219Wu1219@',look_for_keys=False,allow_agent=False)
s=c.open_sftp()
s.put(r'A:\NetSarang\Xftp 8\Temporary\some_file.json','/config/some_file.json')
print('Done:',s.stat('/config/some_file.json').st_size,'bytes')
s.close();c.close()
"
```
