# Workflow Profile 规范

## 用途

Profile 只回答“这一套环境要调用哪四个阶段 Skill，以及通用闸门和目录怎么配置”。人物身份、声音/肖像授权证据、参考素材、Cookie、令牌和项目商业信息属于每次任务的私有 `project-brief.md` 或本地运行配置，不写入可开源 Profile。

## 必需字段

- `schema_version`：当前固定为 `1`。
- `profile_id`：小写字母、数字和连字符组成的稳定 ID。
- `stage_execution`：必须为 `serial`。
- `entry_modes`：固定支持 `full`、`from_script`、`from_audio`、`packaging_only`。
- `stage_skills`：必须包含 `rewrite`、`voice`、`avatar`、`packaging`；每项至少包含 `skill`。
- `gates`：不得弱化合法使用、身份授权及六个生产闸门。
- `policies`：固定发行完整性、运行预检、资产中心、每任务订单、路径+哈希交接、逐阶段估时、`needs_update` 版本语义、首次启用状态、声音风格一次确认、长期 Profile 复用、模块独立启用，以及授权、安全、画面、包装和标识规则。
- `artifact_integrity.algorithm`：当前为 `sha256`。
- `paths`：建议使用相对路径；实际绝对路径放在不提交的本地副本中。
- `privacy`：三项必须为 `false`，防止身份资产、参考声或密钥进入开源包。

## 标准 Profile

```json
{
  "schema_version": 1,
  "profile_id": "my-digital-human-stack",
  "stage_execution": "serial",
  "entry_modes": ["full", "from_script", "from_audio", "packaging_only"],
  "stage_skills": {
    "rewrite": {"skill": "your-video-rewrite-skill"},
    "voice": {"skill": "your-authorized-voice-skill"},
    "avatar": {
      "skill": "digital-human-avatar-musetalk",
      "bundled_path": "bundled-stages/digital-human-avatar-musetalk"
    },
    "packaging": {"skill": "your-video-packaging-skill"}
  },
  "gates": {
    "lawful_use_declaration": "explicit_user",
    "identity_authorization": "verified_before_media_processing",
    "script_approval": "explicit_user",
    "audio_approval": "explicit_user",
    "avatar_qa": "required",
    "avatar_approval": "explicit_user",
    "packaging_sample": "internal_required",
    "final_delivery_qa": "required"
  },
  "policies": {
    "distribution_verification": "required_before_onboarding",
    "runtime_preflight": "required_before_stage_execution",
    "end_to_end_ready_claim": "only_after_all_stage_checks",
    "first_run_onboarding": "required_local_status",
    "asset_center": "local_profile_index",
    "task_order": "required_for_every_run",
    "cross_stage_handoff": "path_hash_no_copy_paste",
    "estimate_before_stage_or_retry": "required",
    "user_facing_estimate": "simple_stage_range",
    "feedback_logs": "per_module_scoped",
    "offline_behavior": "show_network_issue_disable_generation",
    "quality_semantics": "needs_optimization_not_broken",
    "project_change_semantics": "needs_update_preserve_history",
    "material_collection": "disclose_all_collect_by_stage",
    "profile_reuse": "persistent_until_recalibration_required",
    "module_activation": "independent_by_entry",
    "voice_style_confirmation_scope": "once_per_valid_voice_profile",
    "voice_style_reprompt_each_project": false,
    "intake_disclosure": "full_requirements_upfront_by_entry",
    "third_party_identity": "verified_consent_required",
    "prohibited_use_handling": "stop_and_record",
    "maintainer_mode": "local_open_source_no_uploads_by_default",
    "creator_profile": "quick_or_pro",
    "voice_calibration": "three_style_first_confirmation",
    "pronunciation_research": "chinese_context_online_required",
    "avatar_capture": "pre_recording_brief_then_mouth_only_qa",
    "sensitive_data_storage": "local_private_by_default",
    "packaging_layout_selection": "disabled",
    "packaging_canvas": "1080x1920",
    "packaging_person_position": "bottom_right",
    "packaging_cover": "required",
    "generated_content_disclosure": "required"
  },
  "artifact_integrity": {"algorithm": "sha256"},
  "paths": {
    "project_root": "./projects",
    "delivery_root": "./delivery"
  },
  "privacy": {
    "commit_identity_assets": false,
    "commit_reference_voice": false,
    "commit_secrets": false
  }
}
```

## 绑定规则

- `skill` 必须写实际可发现的 Skill 名称，不写机器绝对路径，也不把 Skill 内容复制进 Profile。随总包发行的阶段可以额外写相对总包根目录的 `bundled_path`；默认画面阶段固定为 `digital-human-avatar-musetalk`。
- 总控不会修改绑定 Skill；进入阶段时只读取并执行它。
- 安装或升级总控时，`install_bundled_stage_skills.py` 会把受总控管理的公共画面阶段复制到同一 Codex Skills 目录；旧工作区中精确的 `your-digital-human-video-skill` 示例绑定由迁移脚本更新，用户自定义真实绑定不覆盖。
- 本地专用 Skill 可以直接绑定。开源发布时只提交不含个人资产的通用示例，不提交专用 Profile。
- 阶段 Skill 没有版本字段时，在交接物中写 `unknown`，并可额外记录其 `SKILL.md` SHA-256。
- Profile 只能加强闸门。被绑定 Skill 要求额外人工确认、样片或 QA 时继续保留。
- `maintainer_mode` 只描述公共开源默认。提供托管、代制作或远程处理时必须另建服务 Profile、服务协议和合规合同，不能继续声称“不接收上传”。
- 首次启用状态保存在用户工作区，不保存在 Skill 安装目录。未选择模块为 `not_selected`，不能阻塞无关入口；相关模块进入生产前必须变为 `ready`。
- 公共流程不提供包装版式选择。需要另一种定制版式时，应建立独立包装 Skill 或另开定制工程，而不是在本总控里重新开放选择。

## 专用流程的无改动接入

任何现有四阶段 Skill 都不需要修改。使用者只在本地私有 Profile 中填写实际 Skill 名称；总控进入阶段时读取并执行原 Skill，再用通用交接物引用其输出。

如果某个专用包装 Skill 内部仍有历史版式选择，本地适配器必须显式选择“1080×1920、人物右下、黑色背景、青蓝强调、统一封面”的对应实现；公共用户界面只显示“剪辑包装”。
