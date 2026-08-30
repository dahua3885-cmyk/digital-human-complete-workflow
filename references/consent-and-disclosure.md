# 声音、肖像授权与合成内容标识

> 本文件是开源工作流的安全默认，不替代面向具体国家、地区、平台或业务的法律意见。

## 强制原则

- 声音与肖像分别取得授权；同一份文件可以承载两项，但权限必须分别列明。
- 人物本人上传素材也要留下自我授权声明，避免后续无法证明用途范围。
- 不是本人、无法联系本人、身份无法核验或授权范围不清时停止。
- 未成年人、已故者、公众人物、客户/当事人或跨境传输属于高风险情形，默认停止并要求更明确的法律依据和授权。
- 不能把“素材公开可见”“朋友发给我”“不商用”视为可以克隆声音或操控肖像。

## 每次任务的 `consent-record.json`

从 [示例](../assets/consent-record.example.json) 复制到项目私有目录并补齐真实信息。
具体保存位置、开源默认不接收上传及未来托管服务的安全门槛见 [私有资料存储](storage-and-scale.md)。

至少记录：

```json
{
  "schema_version": 1,
  "subject": {"name": "...", "relationship": "self|third_party"},
  "permissions": {
    "voice_clone": true,
    "likeness_lip_sync": true,
    "video_editing": true,
    "publication": true,
    "commercial_use": false,
    "model_training": false,
    "transfer_to_others": false,
    "platforms": ["..."],
    "territory": "...",
    "starts_at": "ISO-8601",
    "expires_at": "ISO-8601 or null"
  },
  "notice": {
    "purpose": "...",
    "processing_method": "voice cloning and mouth-only lip sync",
    "data_categories": ["voice", "face video"],
    "storage_location": "local|named-provider",
    "retention": "...",
    "rights_and_risks_explained": true
  },
  "evidence": {
    "type": "self_declaration|signed_document|recorded_consent",
    "path": "...",
    "sha256": "...",
    "confirmation_text": "授权原话",
    "confirmed_at": "ISO-8601"
  },
  "revocation": {"method": "...", "contact": "..."}
}
```

授权记录含个人信息，不进入公开仓库。声音、肖像素材和授权证据任一主体不一致时停止。

## 发布标识

- 导出文件和发布流程保留“AI 生成/合成”显式提示及平台要求的声明。
- 能写入元数据时加入生成合成属性、工作流/工具标识和内容编号；保留 `delivery-manifest.json` 作为内部追溯。
- 不删除、篡改、伪造或隐藏平台/服务已经添加的标识。

## 中国境内使用的官方依据

- 《个人信息保护法》第二十八至三十条把生物识别信息列为敏感个人信息，并要求特定目的、充分必要、严格保护和单独同意：<https://www.npc.gov.cn/WZWSREL25wYy9jMi9jMzA4MzQvMjAyMTA4L3QyMDIxMDgyMF8zMTMwODguaHRtbD9yZWY9aW1i>
- 《互联网信息服务深度合成管理规定》第十四条明确涉及人脸、人声编辑时应告知被编辑个人并取得单独同意；第十六、十七条规定合成标识：<https://www.cac.gov.cn/2022-12/11/c_1672221949354811.htm>
- 《人工智能生成合成内容标识办法》自 2025-09-01 起施行，规定显式与隐式标识，并要求发布者主动声明：<https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm>
- 《民法典》第一千零一十九条要求未经同意不得制作、使用、公开他人肖像，并禁止利用信息技术伪造方式侵害肖像权；自然人声音保护参照肖像权规则。
