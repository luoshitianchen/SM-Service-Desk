# 服务台服务 运维手册（OPERATIONS）

> 服务：sm-service-desk（端口 8027）　版本：2.1.0

## 1. 服务概述与依赖

- 定位：SM 平台协作智能微服务，承接 服务台 业务能力。
- 上游：API-Gateway。
- 下游依赖：PostgreSQL（数据库 sm_service_desk）、SM-Audit-Log-Center（审计）、SM-IAM（认证）、Vault（密钥）。
- 部署形态：Kubernetes Deployment + HPA（2~10 副本），GitOps 由 ArgoCD 同步。

## 2. SLO 定义

| 指标 | 目标 |
| --- | --- |
| 可用性 | ≥ 99.9% |
| P99 延迟 | < 1s |
| 错误率 | < 0.1% |

## 3. 错误预算公式与消耗跟踪

错误预算 = 一个月内允许不可用时长。以 99.9% 可用性计算：
- 月允许不可用 ≈ 30 × 24 × 60 × (1 − 0.999) ≈ **43.2 分钟/月**。
- 消耗跟踪：监控看板按周统计实际不可用时长 / 43.2 分钟，超过 50% 须冻结非必要变更。

## 4. 变更管理流程（CAB）

- 所有生产变更须提交变更单，经 CAB 评审。
- 变更窗口：工作日 10:00–16:00（避免早晚高峰与跨日）。
- 高风险变更（数据库结构变更、密钥轮换）须双人复核并安排回滚预演。

## 5. 发布审批流程（dev→staging→prod）

```
dev（自动部署） → staging（人工冒烟通过） → prod（CAB 审批 + 灰度）
```
- 每一道门禁不通过不得进入下一环境。
- prod 采用滚动/灰度发布，先 1 副本验证再全量。

## 6. 回滚流程

1. 触发：冒烟失败 / 错误率突增 / P99 超阈值。
2. 步骤：`helm rollback <release> <revision>` 或 ArgoCD 一键回退上一版本。
3. RTO 目标：≤ 10 分钟。
4. 验证：回滚后执行冒烟测试 + 核对监控指标恢复正常。

## 7. 值班与告警响应

- 实行 7×24 on-call 轮值。
- 告警分级：P1（服务不可用）立即响应，15 分钟内升级到负责人；P2（性能劣化）1 小时内处理；P3（提示）工作时间处理。
- 升级路径：值班 → 服务负责人 → 平台负责人 → CTO。

## 8. 日常运维操作手册

- 查日志：`kubectl logs -n sm-prod deploy/<release> -f`（Promtail 已统一采集至 Loki）。
- 查 Pod：`kubectl get pods -n sm-prod -l app.kubernetes.io/name=sm-service-desk`。
- 扩缩容：调整 HPA 或 `kubectl scale`，变更走变更单。
- 密钥轮换：在 Vault 更新后，ExternalSecret 自动同步，滚动重启 Pod 生效。

