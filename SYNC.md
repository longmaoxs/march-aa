# 同步到 GitHub

仓库地址：<https://github.com/longmaoxs/march-aa>（远程走 SSH：`git@github.com:longmaoxs/march-aa.git`）

本地目录：`/Users/louis/workspace/skills/march-skills/march-aa`

## 认证：SSH（已配置好）

本机已生成密钥 `~/.ssh/id_ed25519`（无口令），公钥已贴到 GitHub 账号。
验证：

```bash
ssh -T git@github.com     # 期望：Hi longmaoxs! You've successfully authenticated...
```

远程已设为 `git@github.com:longmaoxs/march-aa.git`，**不需要 token**。

> 换机器时：`ssh-keygen -t ed25519 -C "you@host" -f ~/.ssh/id_ed25519 -N ""`，
> 把 `~/.ssh/id_ed25519.pub` 贴到 <https://github.com/settings/ssh/new> 即可。

## 提交身份（别改错）

本仓库的 `user.name` / `user.email` 写在**仓库级** config 里：

```
user.name  = Louis
user.email = 356496579+longmaoxs@users.noreply.github.com
```

`@users.noreply.github.com` 是按**用户名**分配的，不能随便编：`louis@users.noreply.github.com`
属于另一个登录名为 `louis` 的账号，用它提交，GitHub 会把 commit 算到那个人名下
（Contributors 里出现 "Louis Gates"）。自己的正确形式是
`<数字ID>+<登录名>@users.noreply.github.com`。

换机器或重新克隆后，进目录先跑一次：

```bash
git config user.name  "Louis"
git config user.email "356496579+longmaoxs@users.noreply.github.com"
```

也可以去 GitHub 设置里勾 *Keep my email addresses private*，它会把这个邮箱显示给你。

> 2026-11 账号已由 `Longmaoxs` 改名为 `longmaoxs`（用户 ID 不变）。改名后无需改写历史：
> noreply 邮箱里真正标识身份的是前面的数字 ID，旧提交里的 `…+Longmaoxs@…` 依然归到同一账号。
> 只需把 remote、`user.email` 和文档里的拼写换成小写。

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
