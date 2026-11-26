# 同步到 GitHub

仓库地址：<https://github.com/Longmaoxs/march-aa>（远程走 SSH：`git@github.com:Longmaoxs/march-aa.git`）

本地目录：`/Users/louis/workspace/skills/march-skills/march-aa`

## 认证：SSH（已配置好）

本机已生成密钥 `~/.ssh/id_ed25519`（无口令），公钥已贴到 GitHub 账号。
验证：

```bash
ssh -T git@github.com     # 期望：Hi Longmaoxs! You've successfully authenticated...
```

远程已设为 `git@github.com:Longmaoxs/march-aa.git`，**不需要 token**。

> 换机器时：`ssh-keygen -t ed25519 -C "you@host" -f ~/.ssh/id_ed25519 -N ""`，
> 把 `~/.ssh/id_ed25519.pub` 贴到 <https://github.com/settings/ssh/new> 即可。

## 平时

改完代码/文档，一条命令：

```bash
cd /Users/louis/workspace/skills/march-skills/march-aa
./sync.sh "加了塔的密檐参数"
```

`sync.sh` 做三件事：`git add -A` → 有改动就 `commit -m <你的话>` → `git push origin main`。

不传消息时用时间戳：`./sync.sh`

## 只看状态

```bash
git -C /Users/louis/workspace/skills/march-skills/march-aa status -sb
git -C /Users/louis/workspace/skills/march-skills/march-aa log --oneline -5
```

## 注意

- `out/*.png` 已在 `.gitignore` 里（成图不进仓，README 用的是 `docs/preview/*.jpg`）。
- `assets/fonts/LXGWWenKai-Regular.ttf` 有 18MB；不想要就 `git rm --cached` 掉。
