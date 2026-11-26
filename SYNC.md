# 同步到 GitHub

仓库地址：<https://github.com/Longmaoxs/march-aa>

本地目录：`/Users/louis/workspace/skills/march-skills/march-aa`

## 第一次（只需一次）

第一次 `git push` 会让 GitHub 要凭据。**密码位置要填 Personal Access Token（PAT）**，
不是账号密码（GitHub 2021 年就停用密码推送了）：

1. 打开 <https://github.com/settings/tokens> → *Generate new token (classic)*
2. 勾 `repo`（公开仓库也建议勾，够用且最小），有效期按需
3. 生成后复制 `ghp_...`，在推送时的 `Password for 'https://github.com':` 处粘贴

```bash
cd /Users/louis/workspace/skills/march-skills/march-aa
git push -u origin main
```

macOS 的 `osxkeychain` 会把这次凭据存进钥匙串，**以后推送不再问**。

> 想改用 SSH（更省事、不用管 token 过期）：
> `ssh-keygen -t ed25519 -C "louis" -f ~/.ssh/id_ed25519 -N ""`，把 `.pub` 内容贴到
> GitHub → Settings → SSH and GPG keys，然后
> `git remote set-url origin git@github.com:Longmaoxs/march-aa.git`。

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
